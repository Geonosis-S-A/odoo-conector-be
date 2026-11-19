# Contexto del proyecto: Geotime / odoo-conector-be

## Qué es
Backend (`odoo-conector-be`) de **Geotime**, una app de timesheets que sincroniza con **Odoo** vía XML-RPC. Odoo es la fuente de verdad de empleados y jerarquía (managers); Geotime persiste sus propios usuarios/horas y empuja/lee de Odoo.

## Stack
- **FastAPI** + **uv** (gestor de paquetes, NO pip). Server: `uv run fastapi dev`.
- Arquitectura hexagonal por módulo: cada carpeta en `app/<modulo>/` tiene `api/` (routers/schemas), `application/` (use cases/services), `domain/` (entidades/interfaces), `infra/` (implementaciones: DB, Odoo, etc).
- Módulos principales: `auth`, `users`, `timesheet_line`, `project`, `task`, `dashboard`, `employee_price`, `accounting`, `team`, `email`, `saved_prompts`, `timesheet_templates`, `personal_time`, `agent` (fuera de `app/`).
- DB: PostgreSQL (Railway), SQLModel + Alembic para migraciones. En LOCAL se crean tablas automático; en STAGING/PROD se maneja con Alembic.
- Auth: JWT. Roles conocidos: `timesheet_user` (default, rol vacío `[]`), `approver`.
- Ambientes vía env var `ENV`: `LOCAL`, `STAGING`, `PROD` (CORS distinto por ambiente).
- Prefijo API: `/api/v1`.

## Integración con Odoo
- `odoo_client.get_connection()`: crea un `ServerProxy` **nuevo por request** (xmlrpc no es thread-safe; antes compartían uno y daba `CannotSendRequest` bajo concurrencia — arreglado en `6f49833`).
- Módulo custom instalado en Odoo: `geo_timesheet_approver`, agrega campo `x_validated_by` a las líneas de timesheet para que quede el aprobador **real** de Geotime (no el usuario de servicio que usa la integración).
- La jerarquía de equipos (quién es manager de quién) vive en Odoo (`timesheet_manager_id`, `child_of` sobre `parent_id`), no se duplica en Geotime.

## Feature en curso: GEO-953 — Equipos + aprobador real (branch `feature/geo-953-teams-timesheet-approver`)

**Problema de negocio:** Odoo solo permite UN aprobador por empleado. Se necesitaba poder delegar "ver" y "validar" timesheets del equipo a otras personas, sin mantener un roster paralelo en Geotime que se desincronice del organigrama real de Odoo.

**Decisión de diseño (Opción 2, la elegida):** el equipo NO se administra en Geotime. Se calcula en vivo consultando la jerarquía de Odoo (`get_team_users`: `timesheet_manager_id == user` o `child_of`). Lo único que Geotime persiste es un **permiso** por par (líder, miembro) con nivel `view` / `validate`, en la tabla `teammemberpermissionmodel` (migración `f1a2b3c4d5e6`).

### Piezas clave (backend)
- `TeamAccessService` (`app/team/application/team_access.py`): expone `visible_employee_ids`, `validatable_employee_ids` (excluye al validador y a su propio líder — sin auto-aprobación), `visible_team_members`, `can_view_team`, `can_validate_team`. Si el líder no tiene `res.users` vinculado en Odoo → equipo vacío (con log deduplicado). Este fue justamente un bug encontrado: Diana no tenía `res.users` y su equipo resolvía vacío.
- Endpoints `/api/v1/teams/...`:
  - `GET/PUT /mine` — el líder gestiona su propio equipo (id sacado del JWT).
  - `GET/PUT /{leaderId}` — mismo, pero para rol `approver` gestionando el equipo de otro.
  - `GET /my-access` → `{is_leader, can_view_team, can_validate_team, members[]}`, pensado para que el front sepa qué mostrar (gating de UI).
- `GET /timesheet/?team=true`: cada línea devuelve `can_validate: bool`. Admin ve `!validated` siempre; para miembro/líder solo si `employee_id` está en `validatable` y `!validated`, y solo cuando se pide `team=true`.
- `POST /timesheet/validate`: respeta los permisos (403/422 si está fuera de alcance).

**Estado:** backend completo y commiteado hasta `6f0f02d`, pusheado y deployado en staging. **Falta merge a `main`.**

### Estado del front (repo aparte)
- El dev del front ya integró `canApproveTimesheetRow(t) = t.can_validate ?? t.is_approver ?? false` (reemplazando `is_approver`, que nunca existió en la API real) y usa `/teams/my-access` para mostrar el menú "Gestión de equipo". Confirmado que lee `can_validate` por fila.
- **Pendiente:** gating del chip "Mi equipo" para no-líderes en `ValidationFiltersAside.tsx` — hoy siempre se puede quitar el filtro aunque el backend igual devuelva 403/vacío si un no-líder lo saca (es solo tema de UX, backend ya está protegido). El dev está esperando confirmación para tocar esa branch.

### Verificado end-to-end en staging (2026-09-08/09)
Miembro con permiso `validate` aprobó desde el front una hora pendiente de otro miembro del equipo; la hora viajó a Odoo con `validated=True` y `x_validated_by` quedó con el nombre real del aprobador (no el service user).

### Pendientes / issues abiertos
1. **500 intermitente "Error al conectar con Odoo"**: nunca se vio el traceback real, el `except Exception` genérico en `odoo_client.get_connection()` lo enmascara. Sospecha: el `ServerProxy` por request podría generar "connection storms" bajo ráfagas del front. Mejora propuesta: no enmascarar el `HTTPException` de `authenticate()`, e incluir `str(e)` en el detail para poder diagnosticar.
2. El front ató el botón **eliminar** a `canApproveTimesheetRow` — acoplamiento indebido (oculta eliminar en filas propias que no son de equipo). Hay que avisarles que usen su propia regla para delete.
3. Bug preexistente y separado: `dashboard_service.py:292` hace `task_id=int(uuid.uuid4())` para "Sin tarea", lo que genera números como `1.6e38` en `/dashboard/summary` y puede romper el render de "Mi actividad" en el front. Ticket aparte, no relacionado a GEO-953.
4. `GET /employees-price/` (pantalla `/team-configuration`, solo rol `approver`) **no se migró** a `TeamAccessService`, sigue usando `get_team_users` directo. Bug latente ahí: pasa `employee_id` como primer argumento pero internamente se compara contra `timesheet_manager_id` (que es un `res.users`), así que esa rama del filtro nunca matchea — solo funciona por `child_of`. Merece ticket propio.

### Cómo diagnosticar si el deploy de staging está atrasado
`GET https://conecta-timesheet-staging-be.soportegeonosis.com.ar/openapi.json` y buscar `can_validate` en `components.schemas.DetailedTimesheetLineResponse`. Si no aparece, el deploy quedó atrás. **Ojo:** el botón "Redeploy" de Railway re-despliega el mismo commit anterior, no el último — hay que usar "Deploy latest commit" o dejar que el push dispare el build automáticamente. El `/health` no sirve para esto (siempre devuelve `version: "1.0.0"` fijo).

### Ambientes / accesos de staging
- Backend: `https://conecta-timesheet-staging-be.soportegeonosis.com.ar/api/v1`
- Front: `https://conecta-timesheet-staging.soportegeonosis.com.ar`
- Infra: Railway (servicio `conecta-timesheet-staging-be`), DB Postgres en Railway.
- Usuarios de prueba (Geotime DB, tabla `usermodel`, password hasheado con `crypt(pw, gen_salt('bf',12))`, requiere extensión `pgcrypto`):
  - `luca.valente@geonosis.com.ar` (emp Odoo 1448)
  - `valentina.cisneros@geonosis.com.ar` (emp 1455)
  - `ivan.tomaselli@geonosis.com.ar` (PO, emp 1389) — gerente real en Odoo, resuelve equipo como líder.
  - `guido.santillan@geonosis.com` — subordinado de Ivan en el Odoo de staging para pruebas end-to-end.
  - Reset de password: `UPDATE usermodel SET hashed_password = crypt('<pass>', gen_salt('bf',12)), updated_at = now() WHERE email = '<email>';`
- Nota infra: los 500 intermitentes que se vieron hace unos días en `/users/employees`, `/teams/mine`, `/projects/`, `/employees-price/` fueron por un cambio de dirección de staging (ya resuelto), no por el bug de concurrencia.

## Feature en curso: GEO-954 — Equipos por proyecto (branch `feature/geo-954-project-assigment`)

**Importante:** GEO-953 (arriba) **nunca se mergeó a `main`** — quedó solo en la cadena de commits que esta rama continúa. O sea, "equipo por jerarquía de departamentos" nunca llegó a producción. GEO-954 lo reemplaza por completo antes de que GEO-953 llegue a mergearse, así que el front no tiene que integrar dos sistemas en secuencia: todo lo de equipos que se construya ahora ya es sobre el criterio nuevo (proyectos).

**Problema de negocio:** un líder deja de ser "quien figura como jefe en la jerarquía de Odoo" y pasa a ser "quien gerencia un proyecto" (`project.project.user_id`) con gente asignada vía `project.assignment`. `GET /employees-price/` también se migró a este criterio (bug latente de GEO-953 documentado ahí arriba, punto 4 de "Pendientes" — **ya resuelto** en `53a5459`).

### Piezas clave (backend)
- `TeamAccessService` (`app/team/application/team_access.py`) ahora resuelve `get_led_team` contra `ProjectAssignmentGateway.get_team_users`, no contra jerarquía.
- Endpoints nuevos: `GET /teams/mine/projects` (cualquier autenticado) y `GET /teams/{leader_id}/projects` (rol `approver`) — equipo agrupado por proyecto, `TeamProjectView`. No aceptan `date_from`/`date_to` (siempre hoy). `members[]` no trae `level`.
- `POST /timesheet/` valida asignación vigente al `project_id`: `EmployeeNotAssignedToProjectError` → **403**, exclusivo de ese caso en ese endpoint (confirmado revisando todos los excepts del router).
- `POST /timesheet/validate` ya autorizaba por gerencia de proyecto antes de esta rama (`can_validate_team`, GEO-953) — un líder no-admin puede validar horas de su equipo sin rol `timesheet_admin`. No requirió cambios para GEO-954.

### Estado del front (repo `odoo-fe/odoo-conector-fe`, branch `feature/geo-954-projects-team`)
Ya tiene bastante hecho (sin commitear al momento de escribir esto): `src/features/teams/{teamsTypes.ts,teamsService.ts,TeamProjectsPage.tsx}`, ruta `/my-team` wireada en `AppRoutes.tsx`, manejo del 403 nuevo en `useTimesheetServices.ts` y `DashboardUser.tsx`.

### Pendientes / fixes a hacer
1. **`teamsTypes.ts` (front) tipa `name`/`email` de `TeamProjectMember` como `string` obligatorio** — el backend los declara `Optional[str] = None` (pueden venir `null`). Ajustar el tipo a `string | null` y que `TeamProjectsPage.tsx` (`getInitials`, render del email) tolere `null`.
2. **`GET /users/employees` no tiene ningún control de autorización más allá de estar autenticado** (confirmado en `app/users/api/routers.py:63-66` y en el use case: sin chequeo de rol ni de pertenencia a equipo). Cualquier usuario logueado puede bajarse el directorio completo (id, nombre, email) de todos los empleados. No es una regresión de esta rama — ya era así — pero la pantalla nueva de validación (accesible ahora a líderes no-admin) lo expone a más gente. Severidad baja (solo nombre/email, requiere auth), pero viola mínimo privilegio. Pendiente: decidir si se restringe a rol/equipo o se deja así a propósito.
3. **Revisar `app/timesheet_line/tests` por el mismo patrón de mocks desactualizados** que encontré en `employee_price` (tests que patcheaban `OdooTimesheetLineGateway.get_team_users` en vez del gateway nuevo). Lo identifiqué como sospecha pero no llegué a confirmarlo ahí — quedó pendiente de la sesión anterior.
4. **Checklist para armar usuarios de prueba en Odoo staging** (causó dos falsos negativos ya, incluido uno el 2026-09-24 con la propia Diana): antes de probar "soy líder/gerente de proyecto", confirmar que la ficha `hr.employee` de ese usuario tiene el campo **"Usuario relacionado"** completo y apuntando exactamente al mismo login que se puso como "Gerente de proyecto". Ser "Usuario interno" no alcanza — son campos distintos. Sin esto, `get_user_id_by_employee_id` devuelve `None` y tanto `/projects/` como `/teams/*` resuelven vacío aunque todo lo demás esté bien configurado.

## Metodología de trabajo preferida
Antes de implementar, entrevistar exhaustivamente y explorar el codebase primero en vez de asumir.
