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
| VT-12 | SSRF en agente IA con bypass de filtro LLM (IP decimal) | 9.0 | GEO-1388 | ⏳ |
| VT-03 | Swagger `/docs` y `/openapi.json` públicos en producción | 8.2 | GEO-1387 | ✅ |

### Altas (CVSS 7.0–8.5)

| ID | Vulnerabilidad | CVSS | Linear | Estado |
|----|----------------|------|--------|--------|
| VT-04 | IDOR escritura de timesheets (PUT + DELETE) | 8.1 | GEO-1389 | ✅ |
| VT-08 | 9.057 timesheets expuestos sin filtro/paginado | 8.0 | GEO-1394 | ⏳ |
| VT-17 | Export Excel masivo con costos ARS/USD sin scope | 7.9 | — | ⏳ |
| VT-15 | HTTP Parameter Pollution con `employee_id[]` | 7.8 | — | ⏳ |
| VT-05 | Sin rate limiting en endpoints de autenticación | 7.5 | GEO-1390 | ⏳ |
| VT-06 | Enumeración de usuarios + roles | 7.5 | GEO-1396 | ⏳ |
| VT-14 | BFLA: validar timesheets ajenos | 7.1 | GEO-1392 | ✅ |
| VT-07 | Headers de seguridad ausentes | 6.5 | — | ⏳ |

### Medias

| ID | Vulnerabilidad | CVSS | Linear | Estado |
|----|----------------|------|--------|--------|
| VT-11 | OTP de 6 dígitos sin lockout | 6.0 | GEO-1390 | ⏳ |
| VT-16 | IDOR en `/dashboard/summary/{employee_id}` | 5.5 | — | ⏳ |
| VT-09 | Email spoofing en `/email/support-mail` | 5.4 | — | ⏳ |
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
