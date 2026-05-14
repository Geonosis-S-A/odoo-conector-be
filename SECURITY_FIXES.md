# Remediación de Vulnerabilidades — Pentest GeoTimesheet 2026-04

Seguimiento de las correcciones derivadas del pentest de Seguridad IT
(Pablo Averbuj Sosto, 22–23 de abril de 2026). Para detalle técnico de cada
fix ver el comentario del Linear correspondiente y el commit referenciado.

| Sistema | GeoTimesheet (`geo-timesheet.soportegeonosis.com.ar`) |
|---|---|
| Backend | `geo-timesheet-be.soportegeonosis.com.ar` (FastAPI / Railway) |
| Frontend | React + Vite |
| Vulnerabilidades | 17 confirmadas + 6 vectores adicionales |
| Nomenclatura | `VT-XX` (Vulnerabilidad Timesheet XX) |

Leyenda: ✅ Resuelto · 🟡 En progreso · ⏳ Pendiente · 🔒 Infraestructura

## Estado

### Críticas (CVSS ≥ 9.0)

| ID | Vulnerabilidad | CVSS | Linear | Estado |
|----|----------------|------|--------|--------|
| VT-01 | Account Takeover vía `/auth/register` (sin OTP) | 9.8 | GEO-1385 | ✅ |
| VT-02 | Fuga de tarifas salariales (`/employees-price/*`) | 9.1 | GEO-1403 | ✅ |
| VT-12 | SSRF en agente IA con bypass de filtro LLM (IP decimal) | 9.0 | GEO-1388 | ✅ |
| VT-03 | Swagger `/docs` y `/openapi.json` públicos en producción | 8.2 | GEO-1387 | ✅ |

### Altas (CVSS 7.0–8.5)

| ID | Vulnerabilidad | CVSS | Linear | Estado |
|----|----------------|------|--------|--------|
| VT-04 | IDOR escritura de timesheets (PUT + DELETE) | 8.1 | GEO-1389 | ✅ |
| VT-08 | 9.057 timesheets expuestos sin filtro/paginado | 8.0 | GEO-1394 | ✅ |
| VT-17 | Export Excel masivo con costos ARS/USD sin scope | 7.9 | — | ✅ |
| VT-15 | HTTP Parameter Pollution con `employee_id[]` | 7.8 | GEO-1391 / GEO-1394 | ✅ |
| VT-05 | Sin rate limiting en endpoints de autenticación | 7.5 | GEO-1390 | ⏳ |
| VT-06 | Enumeración de usuarios + roles | 7.5 | GEO-1396 | ✅ |
| VT-14 | BFLA: validar timesheets ajenos | 7.1 | GEO-1392 | ✅ |
| VT-07 | Headers de seguridad ausentes | 6.5 | GEO-1395 | ✅ |

### Medias

| ID | Vulnerabilidad | CVSS | Linear | Estado |
|----|----------------|------|--------|--------|
| VT-11 | OTP de 6 dígitos sin lockout | 6.0 | GEO-1390 | ⏳ |
| VT-16 | IDOR en `/dashboard/summary/{employee_id}` | 5.5 | — | ⏳ |
| VT-09 | Email spoofing en `/email/support-mail` | 5.4 | — | ✅ |
| VT-13 | IDOR en `DELETE /agent/conversation/{id}` | 5.3 | — | ⏳ |
| VT-10 | Script Lovable.dev sin SRI | 5.0 | — | ⏳ |

### Acciones de infraestructura (fuera de código)

| Acción | Estado |
|---|---|
| Reset de contraseñas comprometidas (`pablo.sosto`, `gabriel.gugliotella`) | 🔒 |
| Conditional Access en Entra ID: MFA obligatorio + bloqueo legacy auth | 🔒 |
| IMDSv2 enforced en Railway / bloqueo de IMDS desde la app | 🔒 (GEO-1402) |
| SRI o migración fuera de Lovable/GPT Engineer en el frontend | 🔒 |

---

## Resueltos

### VT-03 — Swagger / OpenAPI público en producción

**CVSS:** 8.2 · **Linear:** GEO-1385 · **Fix:** 2026-05-11

**Problema.** FastAPI exponía `/docs`, `/redoc` y `/openapi.json` sin auth.
El branch que debía deshabilitarlos comparaba `ENV != "production"`, pero el
valor real de la env var era `"PROD"` → el branch jamás se ejecutaba. Además,
solo se intentaba ocultar `/docs` y `/redoc`, no `/openapi.json`.

**Solución.** Normalización con `.upper()`, constante `IS_PROD` única fuente
de verdad, y los tres endpoints quedan en `None` cuando `IS_PROD`.
Archivos: `app/main.py`.

---

### VT-01 — Account Takeover vía `POST /auth/register`

**CVSS:** 9.8 · **Linear:** GEO-1385 · **Fix:** 2026-05-11

**Problema.** El endpoint seteaba password sin validar OTP, lo que permitía
tomar control de cualquier cuenta existente. El frontend ya usa otro flujo
(`/auth/register/request-otp` → `/auth/password-recovery/verify` →
`/auth/password-recovery/reset`), así que el endpoint vulnerable era código
muerto consumido sólo por el atacante.

**Solución.** Eliminación quirúrgica del endpoint, su `RegisterUseCase`, sus
schemas (`CreateUserRequest`, `RegisterResponse`) y los tests asociados. En
el frontend se ajustó `noAuthEndpoints` para listar explícitamente los
endpoints públicos (antes el prefijo `"/auth/register"` matcheaba por
coincidencia parcial varios endpoints).
Archivos: `app/auth/api/routes.py`, `app/auth/api/schemas.py`,
`odoo-conector-fe/src/lib/api.ts`.

---

### VT-02 — Fuga de tarifas salariales en `/employees-price`

**CVSS:** 9.1 · **Linear:** GEO-1403 · **Fix:** 2026-05-11

**Problema.** El reporte señalaba `GET /employees-price/`, pero ese endpoint
**sí** filtraba por equipo. Los IDORs reales (no listados explícitamente)
estaban en `GET /employees-price/history/{employee_id}` y
`POST /employees-price/`: solo validaban rol `approver` y no la pertenencia
del target al equipo del solicitante. Cualquier approver podía leer o
sobrescribir el costo por hora de cualquier empleado.

**Solución.** Nuevo helper `app/shared/security/authorization.py` con
`ensure_employee_in_team(...)` (self + subordinados directos/descendentes
vía `child_of` de Odoo). Aplicado **antes** del lookup en BD para que la
diferencia 403 vs 404 no permita enumerar IDs. 7 tests de regresión IDOR.
Archivos: `app/employee_price/api/routers.py`,
`app/shared/security/authorization.py`.

---

### VT-04 — IDOR de escritura en `/timesheet` (PUT y DELETE)

**CVSS:** 8.1 · **Linear:** GEO-1389 · **Fix:** 2026-05-11

**Problema.** Tres vectores:
1. `PUT /timesheet/{id}` no verificaba ownership → cualquiera podía editar el
   timesheet de cualquier empleado.
2. El body de `EditTimesheetRequest` traía `employee_id` y permitía
   transferir un timesheet propio a un tercero (IDOR de integridad).
3. **Hallazgo extra:** `DELETE /timesheet/` tenía el mismo IDOR sin
   documentar — recibía lista de IDs y borraba sin validar dueño.

**Solución.** Refactor del helper a `TeamScope` + `get_team_scope(...)` +
`ensure_owns_timesheets(...)` (batch sin N+1 a Odoo). En PUT se valida
ownership y se bloquea la mutación de `employee_id`. En DELETE se aplica el
scope al lote con semántica all-or-nothing. 13 tests de regresión.
Archivos: `app/timesheet_line/api/routers.py`,
`app/shared/security/authorization.py`.

---

### VT-08 — Listado masivo de timesheets (`GET /timesheet/`) + VT-15 (HPP)

**CVSS:** 8.0 (VT-08) / 7.8 (VT-15) · **Linear:** GEO-1394 · **Fix:** 2026-05-12

**Problema (VT-08).** `GET /timesheet/` podía devolver miles de registros en una
sola respuesta; los usuarios con rol approver obtenían efectivamente un
volcado global si no acotaban `employee_id` / equipo.

**Problema (VT-15 / GEO-1391).** Además de valores duplicados de `employee_id`, la
notación `employee_id[]` / `employee_id[N]` hacía que el filtro escalar se perdiera
y el backend respondiera como sin filtro (volcado masivo). **Linear:** GEO-1391.

**Solución.** Respuesta **paginada** obligatoria (`items`, `total`, `page`,
`page_size`, máx. 100 por página). Sin `employee_id` ni `team`, un approver
solo ve sus propios registros (misma línea que VT-04). Parsing centralizado en
`scalar_employee_id_optional`: **un** parámetro `employee_id` entero; claves
`employee_id[]` / `employee_id[…]`, duplicados o no enteros → **HTTP 400**.
Mismo helper en `GET /dashboard/summary/detail` (`employee_id` query).
Caso de uso y gateway Odoo con `count` + `limit`/`offset`. Frontend: `timesheetService`
itera páginas hasta agotar `total`.
Archivos: `app/shared/security/employee_id_query.py`,
`app/timesheet_line/domain/repositories.py`,
`app/timesheet_line/infra/external/odoo/odoo_timesheet_gateway.py`,
`app/timesheet_line/application/use_cases/obtener_horas.py`,
`app/timesheet_line/api/schemas.py`, `app/timesheet_line/api/routers.py`,
`odoo-conector-fe/src/features/timesheets/services/timesheetService.ts`,
`odoo-conector-fe/src/features/validations/services/validationService.ts`,
`app/timesheet_line/tests/api/test_list_timesheet_hpp_vt15.py`.

---

### VT-07 — Headers de seguridad (CSP, X-Frame, nosniff, Permissions-Policy, HSTS)

**CVSS:** 6.5 · **Linear:** GEO-1395 · **Fix:** 2026-05-12

**Problema.** Las respuestas HTTP no incluían cabeceras de endurecimiento habituales
(X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP, etc.), lo que
facilita abusos en contextos de cliente (MIME sniffing, clickjacking, filtrado
de referrer) si la API se consume junto a contenido web.

**Solución.** Middleware Starlette (`SecurityHeadersMiddleware`) registrado en
`app/main.py` tras CORS, que en **todas** las respuestas añade:
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (cámara,
mic, geolocalización, etc. deshabilitados), y `Content-Security-Policy` mínima
para API JSON (`default-src 'none'`, `frame-ancestors 'none'`, `base-uri 'none'`,
`form-action 'none'`). **`Strict-Transport-Security`** sólo si `ENV` es
`PROD` o `STAGING` (HTTPS en despliegue); no en `LOCAL` para no forzar HSTS
sobre HTTP en desarrollo. SRI en scripts del frontend permanece en VT-10.
Archivos: `app/shared/security/security_headers_middleware.py`, `app/main.py`,
`app/tests/test_security_headers_vt07.py`.

---

### VT-09 — Email spoofing en `POST /email/support-mail`

**CVSS:** 5.4 · **Linear:** — · **Fix:** 2026-05-12

**Problema.** El body permitía `user_name` (y fecha) controlados por el cliente;
el correo interno presentaba ese nombre como si fuera quien reportaba, permitiendo
suplantación respecto del equipo de soporte.

**Solución.** `SupportMailRequest` sólo acepta `subject` y `body` (`extra="forbid"`).
`user_name` y `user_email` se toman **exclusivamente** del JWT; la marca temporal del
reporte es `datetime.now(timezone.utc)` en servidor. Plantilla HTML actualizada con
email verificado; envío Resend con `reply_to` al correo del JWT.
Frontend deja de enviar identidad en el payload.
Archivos: `app/email/api/schemas.py`, `app/email/api/routes.py`,
`app/email/infra/email_service.py`, `app/shared/templates/email/support_mail.html`,
`app/tests/test_support_mail_vt09.py`,
`odoo-conector-fe/src/services/reportService.ts`,
`odoo-conector-fe/src/components/ReportIssueButton.tsx`,
`app/timesheet_line/tests/integration/test_review_mail_integration.py` (mock).

---

### VT-17 — Export Excel `/dashboard/export-timesheets` con costos ARS/USD

**CVSS:** 7.9 · **Linear:** — · **Fix:** 2026-05-12

**Problema.** El caso de uso reutilizaba `all_by_employees_with_requester_user_id`,
que en Odoo añade una rama OR: todas las líneas de timesheet sobre proyectos donde
el usuario figura como `user_id`, además del filtro por equipo. Eso puede incluir
cargas de **empleados externos** al equipo pero con proyecto compartido, y el Excel
mezcla **nombre + horas + `costo_por_hora` / USD** derivados de BD local (`employee_price`),
exponiendo información salarial sensible por encima del alcance esperado.

**Solución.** En el router se resuelve el mismo **`TeamScope`** que VT-02/VT-04
(`get_team_scope`) y sólo se consultan líneas `employee_id in {self ∪ team_members}` mediante
`all_by_employees` — sin la rama de proyectos gestionados. Test de regresión del caso de uso.
Archivos: `app/dashboard/api/routers.py`,
`app/dashboard/application/use_cases/export_timesheets.py`,
`app/dashboard/tests/application/use_cases/test_export_timesheets_strict_scope.py`.

---

### VT-12 — SSRF en agente IA con bypass del filtro LLM (IP decimal)

**CVSS:** 9.0 · **Linear:** GEO-1388 · **Fix:** 2026-05-11

**Problema.** El agente IA aceptaba en `description` cualquier URL escrita
por el usuario. Para evitar exfiltración de metadata cloud
(`http://169.254.169.254/...`) se intentó filtrar a nivel **LLM** dentro
del system prompt — el pentest mostró que el filtro se bypassea con la IP
en formato decimal (`http://2852039166/...`), porque el modelo no
"entiende" representaciones numéricas alternativas. Aún no hay un sink HTTP
real en backend que dispare la request, pero el payload tóxico igual se
persistía en Odoo, contaminaba el `pending_confirmation` y dejaba sembrada
una stored-XSS / SSRF latente para cualquier integración futura (preview de
links en mail, autolink en frontend, etc.).

**Solución.** Validación a nivel código en `app/shared/security/url_safety.py`
que detecta IPs hacia recursos internos en **todas** las representaciones
de `inet_aton(3)`: dotted clásico, octetos en hex/octal, entero de 32 bits
en decimal, entero de 32 bits en hex, IPv6 nativo, IPv6 con IPv4 mapped y
hostnames de metadata cloud (`metadata.google.internal`, etc.). Rangos
prohibidos: RFC 1918, link-local (incl. AWS/GCP/Azure), loopback, CGNAT,
ULA. Aplicada en tres capas:
1. Pydantic validator en `CargarHorasRequest.name` y `EditTimesheetRequest.name`
   (cubre el endpoint REST y todo lo que pase por esos schemas).
2. Validación temprana en `prepare_summary` (tool del agente) → fail-fast
   antes del `pending_confirmation`, el usuario nunca ve un confirm con
   payload tóxico.
3. Defensa profunda en `create_timesheet_entries` por si el LLM saltea
   `prepare_summary`.

56 tests unitarios cubren el detector (incluido el payload **literal** del
pentest `2852039166`) + 36 tests de los schemas + 9 tests de las tools.
Archivos: `app/shared/security/url_safety.py` (nuevo),
`app/timesheet_line/api/schemas.py`, `agent/tools/project_tools.py`.

---

### VT-14 — BFLA en `POST /timesheet/validate` (+ bonus en `/review`)

**CVSS:** 7.1 · **Linear:** GEO-1392 · **Fix:** 2026-05-11

**Problema.** Dos vectores en `/timesheet/validate` (y los mismos en
`/timesheet/review`):
1. Solo se chequeaba rol `approver`, no la pertenencia de los timesheets al
   equipo del solicitante → cualquier approver podía validar timesheets de
   empleados de otros equipos.
2. El campo `approver_mail` venía del body, no del JWT → un approver podía
   suplantar a otro: el empleado recibía un correo "tu timesheet fue aprobado
   por `<email_arbitrario>`".

**Solución.** Reuso del helper `ensure_owns_timesheets(...)` ya construido
para VT-04 (mismo `TeamScope`, sin queries extra a Odoo) y validación
explícita de `request.approver_mail == current_user["user_email"]` (cierra
el spoofing). Aplicado a `validate` y a `review` con semántica all-or-nothing
sobre el lote. 8 tests de regresión nuevos.
Archivos: `app/timesheet_line/api/routers.py`.


---

### VT-06 — Enumeración de usuarios + roles via `/users/employees` y `/users/sync/{employee_id}`

**CVSS:** 7.5 · **Linear:** GEO-1396 · **Fix:** 2026-05-14

**Problema.** Tres vectores de exposición de información sensible (OWASP A07:2021):

1. `GET /users/employees` devolvía el directorio completo de los 98 empleados
   (nombre, email corporativo e ID interno de Odoo) a cualquier usuario autenticado,
   independientemente de su rol. Los 98 emails `@geonosis.com.ar` son UPNs del
   tenant de Microsoft 365 y constituyen una lista lista para password spray contra
   `login.microsoftonline.com`.

2. `POST /users/sync/{employee_id}` retornaba en `changes_made.roles` los IDs
   exactos de grupo Odoo del empleado sincronizado (salary, approver, etc.) a
   cualquier usuario autenticado, permitiendo mapear cuentas con privilegios
   elevados antes de atacarlas.

3. En el flujo de login, la excepción `UserInactive` emitía el mensaje interno de
   la excepción (distinto a `"Credenciales inválidas"`), revelando que la cuenta
   existe pero está inactiva (user enumeration por error diferencial).
   El endpoint `POST /auth/password-recovery/request` respondía con `404` y el
   mensaje `"El email no ha sido registrado en el sistema"` cuando el email no
   existía, y `POST /auth/password-recovery/verify` respondía con `404 "User not
   found"` separado del error de OTP inválido.

**Solución.**

*Directorio de empleados — control por rol:*
Nuevo helper `is_privileged_user(user_roles)` en `app/shared/security/roles.py`
que verifica el rol `approver` (el único rol elevado del sistema). El endpoint
`GET /users/employees` bifurca la respuesta:
- **Con rol `approver`** → respuesta completa `EmployeesListResponse` con
  `{id, email, full_name}`.
- **Sin rol `approver`** → respuesta reducida `EmployeesListPublicResponse` con
  solo `{full_name}`, apta para autocomplete en UI sin exponer emails ni IDs
  internos.

*Roles en sync — filtrado por privilegio y ownership:*
El endpoint `POST /users/sync/{employee_id}` omite el campo `roles` de
`changes_made` cuando el solicitante no tiene rol `approver` **y** no está
sincronizando su propia cuenta (compara `current_user["user_id"] == employee_id`).
Un usuario básico puede ver sus propios cambios de rol (autoservicio), pero no los
de terceros.

*Normalización de mensajes de error — anti user-enumeration:*
- `UserInactive` en login → mismo `"Credenciales inválidas"` genérico.
- `POST /auth/password-recovery/request`: ante `UserNotFound` ya no lanza 404;
  devuelve `200` con `"Si el email está registrado, recibirás un código OTP"`
  (patrón estándar de reset seguro).
- `POST /auth/password-recovery/verify`: `UserNotFound` tratado igual que
  `OTPNotFound` → `400 "Invalid OTP"`, sin diferenciar si el email existe.

Archivos: `app/shared/security/roles.py`,
`app/users/api/schemas.py`, `app/users/api/routers.py`,
`app/auth/api/routes.py`.
