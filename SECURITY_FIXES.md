# Remediación de Vulnerabilidades — Pentest GeoTimesheet 2026-04

Documento de seguimiento de las correcciones aplicadas a partir del informe de pentesting
de Seguridad IT (Pablo Averbuj Sosto, 22–23 de abril de 2026).

| Campo | Valor |
|---|---|
| Sistema | GeoTimesheet (`geo-timesheet.soportegeonosis.com.ar`) |
| Backend | `geo-timesheet-be.soportegeonosis.com.ar` (FastAPI / Railway) |
| Frontend | React + Vite |
| Total vulnerabilidades | 17 confirmadas + 6 vectores adicionales |
| Nomenclatura | `VT-XX` (Vulnerabilidad Timesheet XX) |

---

## Estado de las correcciones

Leyenda: ✅ Resuelto · 🟡 En progreso · ⏳ Pendiente · 🔒 Requiere acción de infraestructura/IT (fuera del código)

### Críticas (CVSS ≥ 9.0)

| ID | Vulnerabilidad | CVSS | Estado |
|----|----------------|------|--------|
| VT-01 | Account Takeover vía `/auth/register` (sin verificación de OTP) | 9.8 | ✅ |
| VT-02 | Fuga de tarifas salariales (`/employees-price/*`) | 9.1 | ✅ |
| VT-12 | SSRF en agente IA con bypass de filtro LLM (IP decimal) | 9.0 | ⏳ |
| VT-03 | Swagger `/docs` y `/openapi.json` públicos en producción | 8.2 | ✅ |

### Altas (CVSS 7.0–8.5)

| ID | Vulnerabilidad | CVSS | Estado |
|----|----------------|------|--------|
| VT-04 | IDOR: escritura de timesheets ajenos | 8.1 | ⏳ |
| VT-08 | 9.057 timesheets expuestos sin filtro/paginado | 8.0 | ⏳ |
| VT-17 | Export Excel masivo con costos ARS/USD sin scope | 7.9 | ⏳ |
| VT-15 | HTTP Parameter Pollution con `employee_id[]` | 7.8 | ⏳ |
| VT-05 | Sin rate limiting en endpoints de autenticación | 7.5 | ⏳ |
| VT-06 | Enumeración de usuarios + roles | 7.5 | ⏳ |
| VT-14 | BFLA: validar timesheets ajenos | 7.1 | ⏳ |
| VT-07 | Headers de seguridad ausentes | 6.5 | ⏳ |

### Medias

| ID | Vulnerabilidad | CVSS | Estado |
|----|----------------|------|--------|
| VT-11 | OTP de 6 dígitos sin lockout | 6.0 | ⏳ |
| VT-16 | IDOR en `/dashboard/summary/{employee_id}` | 5.5 | ⏳ |
| VT-09 | Email spoofing en `/email/support-mail` | 5.4 | ⏳ |
| VT-13 | IDOR en `DELETE /agent/conversation/{id}` | 5.3 | ⏳ |
| VT-10 | Script Lovable.dev sin SRI | 5.0 | ⏳ |

### Acciones de infraestructura (fuera de código)

| Acción | Estado |
|---|---|
| Reset de contraseñas comprometidas durante el pentest (`pablo.sosto@geonosis.com.ar`, `gabriel.gugliotella@geonosis.com.ar`) | 🔒 |
| Conditional Access en Entra ID: MFA obligatorio + bloqueo de legacy auth | 🔒 |
| IMDSv2 enforced en Railway / bloqueo de acceso al metadata endpoint desde la app | 🔒 |
| Configurar SRI o migrar fuera de Lovable/GPT Engineer en el frontend | 🔒 |

---

## VT-03 — API Documentation pública sin autenticación

| Atributo | Detalle |
|---|---|
| **Estado** | ✅ Resuelto |
| **Severidad** | CRÍTICO — CVSS 8.2 |
| **OWASP** | A05:2021 — Security Misconfiguration |
| **Endpoints** | `GET /docs`, `GET /redoc`, `GET /openapi.json` |
| **Archivo afectado** | `odoo-conector-be/app/main.py` |
| **Fecha de corrección** | 2026-05-11 |

### Problema

FastAPI habilita por defecto Swagger UI (`/docs`), ReDoc (`/redoc`) y el schema OpenAPI JSON (`/openapi.json`) sin autenticación. Esto exponía:

- 33 endpoints con sus métodos HTTP, parámetros, tipos y modelos Pydantic
- Schemas de request/response (`CargarHorasRequest`, `ChangePasswordRequest`, `CargarHorasAgentRequest`, `ApprovedMailRequest`, entre otros)
- Toda la información necesaria para que un atacante reduzca de horas a minutos su fase de reconocimiento.

### Análisis técnico del bug

El código tenía la intención de deshabilitar la documentación en producción, pero la comparación usaba un **string equivocado**:

```python
docs_url="/docs" if ENV != "production" else None
```

El resto del codebase (`main.py` líneas 82–93, `roles.py`, `project_stages.py`, `config.py`, `README_DATABASE.md`) usa el valor `"PROD"` en mayúsculas. Como `"PROD" != "production"` siempre es `True`, **la rama "deshabilitar" nunca se ejecutaba en producción** y Swagger quedaba activo.

Además, aunque la comparación fuera correcta, **solo se ocultaban `/docs` y `/redoc`**, pero NO `/openapi.json`. El schema JSON contiene exactamente la misma información que el pentester necesitaba enumerar; ocultar solo el UI es seguridad por oscuridad.

### Solución aplicada

Tres cambios en `odoo-conector-be/app/main.py`:

1. **Normalización defensiva de `ENV`** con `.upper()` para evitar futuros desalineamientos por mayúsculas/minúsculas.
2. **Constante `IS_PROD`** como única fuente de verdad sobre "estamos en producción".
3. **Deshabilitar también `openapi_url`** además de `docs_url` y `redoc_url`.

```24:26:odoo-conector-be/app/main.py
ENV = os.getenv("ENV", "LOCAL").upper()  # Por defecto, local
IS_PROD = ENV == "PROD"
API_PREFIX = "/api/v1"
```

```58:68:odoo-conector-be/app/main.py
app = FastAPI(
    title="Odoo Connector API",
    description="API para conectar con Odoo",
    version="1.0.0",
    lifespan=lifespan,
    # En producción deshabilitamos Swagger UI, ReDoc y el schema OpenAPI público
    # para no exponer la superficie completa de la API (VT-03 del pentest 2026-04).
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)
```

### Verificación post-deploy

En **staging** (`ENV=STAGING`), Swagger debe seguir accesible:

```bash
curl -sI https://geo-timesheet-be-staging.soportegeonosis.com.ar/docs        # → 200
```

En **producción** (`ENV=PROD`), los tres endpoints deben devolver 404:

```bash
curl -sI https://geo-timesheet-be.soportegeonosis.com.ar/docs                # → 404
curl -sI https://geo-timesheet-be.soportegeonosis.com.ar/redoc               # → 404
curl -sI https://geo-timesheet-be.soportegeonosis.com.ar/openapi.json        # → 404
```

### Riesgos y regresiones evaluados

| Riesgo | Mitigación |
|---|---|
| Romper el frontend si consumía `/openapi.json` | El frontend consume únicamente `/api/v1/*`. No hay generación de cliente automática que dependa del schema. |
| Romper monitoreo/health checks | No aplica: el monitoreo usa `/health` y `/`, no `/docs`. |
| Romper a los devs que usan Swagger | Cero impacto en LOCAL y STAGING. En producción se pierde Swagger intencionalmente; los devs deben usar staging. |
| Que el `.upper()` afecte otras ramas | Confirmado seguro: los valores en `lifespan`, CORS y resto del código ya estaban en mayúsculas. Ahora es además case-insensitive. |

### Trabajo relacionado pendiente

- VT-06 (enumeración de usuarios): el cierre de Swagger reduce el descubrimiento, pero los endpoints `/users/employees` y `/users/sync/{id}` siguen devolviendo el directorio completo. Se aborda por separado.
- Considerar más adelante un **OpenAPI autenticado** (solo accesible para usuarios con rol admin) si el equipo necesita el schema en producción para integraciones internas.

---

## VT-01 — Account Takeover sin autenticación

| Atributo | Detalle |
|---|---|
| **Estado** | ✅ Resuelto |
| **Severidad** | CRÍTICO — CVSS 9.8 |
| **OWASP** | A07:2021 — Identification and Authentication Failures |
| **CWE** | CWE-287 (Improper Authentication) |
| **Endpoint** | `POST /api/v1/auth/register` |
| **Archivos afectados** | `odoo-conector-be/app/auth/api/routes.py`, `app/auth/api/schemas.py`, `app/auth/application/use_cases/register.py`, `app/auth/tests/integration/test_register_routers.py`, `app/auth/tests/application/use_cases/test_register_use_case.py`, `odoo-conector-fe/src/lib/api.ts` |
| **Fecha de corrección** | 2026-05-11 |

### Problema

El flujo de registro tenía un endpoint `POST /auth/register` que recibía `{email, password}` y **seteaba la contraseña directamente sin verificar OTP**. El propio código lo marcaba como "en desuso" en un comentario, pero seguía montado, expuesto y funcional.

Tal como reporta el pentest:

> Si el email ya existe en la base de datos, el sistema sobreescribe la contrasena sin verificacion.
>
> ```
> POST /api/v1/auth/register
> Body: {"email":"victima@geonosis.com.ar","password":"Nueva1234!","name":"x","last_name":"x"}
> Respuesta: HTTP 200 — cuenta tomada
> ```

### Análisis técnico del bug

Auditando el flujo encontramos:

1. **`POST /auth/register/request-otp`** (`RequestOTPForRegisterUseCase`) crea el usuario en BD con `is_active=False`, guarda el OTP y lo envía por mail. **Hasta acá todo bien.**
2. **`POST /auth/register`** (`RegisterUseCase.execute`) llamaba a `user_repository.set_password(email, hashed_password)` que:
   - Buscaba al `UserModel` por email
   - **Seteaba `hashed_password` y `is_active=True` sin pedir ni validar el OTP**

Esto permitía dos escenarios de ATO:

- **Víctima sin cuenta previa:** el atacante llamaba primero a `/register/request-otp` con el email de la víctima (lo cual creaba al user inactivo), y luego a `/register` para activarlo con cualquier password.
- **Víctima con cuenta activa:** el atacante saltaba directo a `/register` y la lógica sobrescribía la password existente y mantenía/activaba la cuenta.

Adicionalmente, al revisar el frontend descubrimos algo decisivo: **el flujo real de registro no utiliza `POST /auth/register`**. Lo que el frontend hace es:

| # | Página | Endpoint backend | Lo que hace |
|---|--------|------------------|-------------|
| 1 | `RequestOtpPage?register=1` | `POST /auth/register/request-otp` | Crea usuario inactivo + envía OTP |
| 2 | `VerifyOtpPage` | `POST /auth/password-recovery/verify` | Valida el OTP |
| 3 | `SetPasswordPage` | `POST /auth/password-recovery/reset` | Re-valida OTP, setea password, activa cuenta y marca OTP como usado |

El endpoint vulnerable `/auth/register` era literalmente **código muerto**: no lo llama ningún consumidor legítimo, solo el atacante.

### Solución aplicada

**Cirugía mínima: eliminar el endpoint vulnerable y todo su árbol de código asociado.** No tiene sentido "arreglar" un endpoint que ningún cliente legítimo usa; cualquier intento de mantenerlo y agregarle validación de OTP simplemente duplicaría la lógica que ya existe en `/password-recovery/reset`.

**Backend (`odoo-conector-be`):**

1. **Endpoint eliminado** en `app/auth/api/routes.py`. Se reemplazó por un comentario que documenta la decisión y el flujo vigente:

```141:148:odoo-conector-be/app/auth/api/routes.py
# NOTA DE SEGURIDAD (VT-01, pentest 2026-04):
# El endpoint POST /auth/register fue eliminado porque no validaba OTP y permitía
# tomar el control de cualquier cuenta (CVSS 9.8 — Account Takeover).
# El flujo de registro vigente es:
#   1) POST /auth/register/request-otp  (crea usuario inactivo + envía OTP)
#   2) POST /auth/password-recovery/verify  (valida OTP)
#   3) POST /auth/password-recovery/reset   (re-valida OTP, setea password y activa cuenta)
```

2. **Imports limpiados** en `routes.py`: se removieron `CreateUserRequest`, `RegisterResponse` y `RegisterUseCase`.
3. **Schemas eliminados** en `app/auth/api/schemas.py`: clases `CreateUserRequest` y `RegisterResponse`.
4. **Use case eliminado**: archivo `app/auth/application/use_cases/register.py` borrado.
5. **Tests eliminados**: `app/auth/tests/integration/test_register_routers.py` y `app/auth/tests/application/use_cases/test_register_use_case.py` (ambos validaban exactamente la lógica vulnerable, no eran salvables como tests de regresión).

**Frontend (`odoo-conector-fe`):**

6. Se ajustó `noAuthEndpoints` en `src/lib/api.ts` para que matchee endpoints reales en lugar del prefijo genérico `/auth/register`:

```17:28:odoo-conector-fe/src/lib/api.ts
// Endpoints públicos: el interceptor de auth NO debe agregarles el Authorization
// ni intentar refresh-on-401. Antes existía "/auth/register" como prefijo, pero
// ese endpoint fue eliminado por la vulnerabilidad VT-01 (Account Takeover);
// el flujo de registro real es /auth/register/request-otp + /auth/password-recovery/*.
const noAuthEndpoints = [
  "/auth/login",
  "/auth/register/request-otp",
  "/auth/password-recovery/request",
  "/auth/password-recovery/verify",
  "/auth/password-recovery/reset",
  "/auth/refresh",
];
```

Además incluí explícitamente los endpoints de `password-recovery`. Antes no estaban en la lista; funcionaba por accidente (no devuelven 401), pero la nueva lista deja el contrato explícito y robusto a futuras refactorizaciones.

### Verificación post-deploy

Ataque del pentest replicado contra producción luego del deploy:

```bash
curl -i -X POST https://geo-timesheet-be.soportegeonosis.com.ar/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"victima@geonosis.com.ar","password":"Nueva1234!","name":"x","last_name":"x"}'
# Debe responder → HTTP 404 Not Found
```

Suite de tests del módulo auth:

```bash
cd odoo-conector-be
pytest app/auth/tests -q
# 52 passed, 4 warnings in ~6s
```

Flujo legítimo de registro (regresión manual desde la UI):

1. Click en "Registrarse" en `/login` → llega a `/request-otp?register=1`
2. Ingresar email corporativo → debe recibir OTP por mail
3. Verificar OTP en `/verify-otp` → navegar a `/set-password`
4. Ingresar y confirmar password → quedar logueado y redirigido al dashboard

### Riesgos y regresiones evaluados

| Riesgo | Mitigación |
|---|---|
| Romper el alta de usuarios nuevos | El flujo real (`request-otp` + `password-recovery/*`) no se tocó. Tests verdes. |
| Algún cliente externo dependiendo de `POST /auth/register` | Inventario completo del codebase y del frontend: cero referencias. La API estaba documentada como "en desuso" por el propio código. |
| Que el endpoint reaparezca por accidente en el futuro | El comentario en `routes.py` deja la decisión documentada en el lugar exacto donde un dev intentaría agregarlo de vuelta. |
| Tests removidos sin reemplazo | Los tests validaban la lógica vulnerable; mantenerlos sería bloquear el fix. La cobertura del flujo válido (`password_recovery`, `auth_routers`, `change_password`, `refresh`) se mantiene intacta. |
| `noAuthEndpoints` cambia su semántica de matching | Antes `"/auth/register"` matcheaba por prefijo a `request-otp` por coincidencia parcial; ahora se listan ambos endpoints explícitamente. Sin regresión funcional. |

### Trabajo relacionado pendiente

- **VT-11** (OTP brute-forceable sin lockout): aunque ahora el OTP es obligatorio en el flujo de registro, sigue siendo de 6 dígitos sin rate limiting. Combinado con VT-05, un atacante puede probar 1 millón de combinaciones. Se aborda al llegar a VT-11/VT-05.
- **Race condition en OTP** (ataques adicionales del informe): si un atacante envía múltiples requests de `password-recovery/reset` en paralelo con OTPs candidatos antes del fix de rate limiting, el bug podría reaparecer parcialmente. Se mitiga totalmente con VT-05 (rate limiting) + lockout de OTP.
- **Refactor opcional**: el uso del flujo de "password recovery" para activar cuentas nuevas funciona pero es semánticamente confuso. Considerar a futuro un endpoint propio `/auth/register/complete` que reciba `{email, otp_code, password}` y lo manejen explícitamente. Fuera del scope de VT-01.

---

## VT-02 — Fuga de tarifas salariales / IDOR en `employees-price`

| Atributo | Detalle |
|---|---|
| **Estado** | ✅ Resuelto |
| **Severidad** | CRÍTICO — CVSS 9.1 |
| **OWASP** | A01:2021 — Broken Access Control |
| **CWE** | CWE-639 (Authorization Bypass Through User-Controlled Key) / BOLA |
| **Endpoints** | `GET /api/v1/employees-price/history/{employee_id}`, `POST /api/v1/employees-price/` |
| **Archivos afectados** | `app/employee_price/api/routers.py`, `app/shared/security/authorization.py` (nuevo), `app/employee_price/tests/integration/test_employee_price_routers.py` |
| **Linear** | [GEO-1403](https://linear.app/) |
| **Fecha de corrección** | 2026-05-11 |

### Problema

El reporte original señalaba `GET /api/v1/employees-price/` como un endpoint que devolvía sin restricciones todas las tarifas por hora de la empresa.

> "Cualquier usuario aprobador puede consultar tarifas de toda la empresa".

Esto se interpreta como datos financieros sensibles (costo de personal, base para cálculo de margen, indicador de salarios) expuestos a cualquier usuario aprobador, sin importar si gestiona o no a esos empleados.

### Análisis técnico

Al auditar el módulo `employee_price` encontramos un **matiz importante respecto del reporte original** y **dos IDORs no documentados explícitamente pero más graves**:

#### Hallazgo 1: `GET /employees-price/` **no** era el verdadero problema

Contrario a lo que sugería el reporte, este endpoint **sí** filtra por equipo. El use case `ListTeamEmployeePricesUseCase` resuelve `timesheet_line_gateway.get_team_users(user_id, employee_id)` que usa la jerarquía de Odoo (`timesheet_manager_id` + `child_of`) para devolver únicamente subordinados directos y descendentes. Un approver de un equipo ve solo a su equipo.

> Lo que probablemente vio el pentester durante el assessment es que **un manager con muchísimo equipo bajo su responsabilidad** (caso real: `pablo.sosto@geonosis.com.ar`) recibe una lista enorme — pero estrictamente dentro de su scope. No es una fuga, es scope amplio.

#### Hallazgo 2: IDOR real en `GET /employees-price/history/{employee_id}`

Este endpoint **solo verificaba el rol** (`approver`) y luego consultaba el historial del `employee_id` indicado en el path **sin validar que perteneciera al equipo del solicitante**. Cualquier approver podía pedir el historial salarial completo de cualquier otro empleado (incluso CEOs, directivos, RRHH).

```python
# código vulnerable (antes del fix):
if not is_approver:
    raise HTTPException(403, ...)
user_repository = SQLModelUserRepository(db)
employee_data = user_repository.get_by_id(employee_id)  # ← sin scope check
# devuelve el historial completo
```

#### Hallazgo 3: IDOR real en `POST /employees-price/`

El endpoint de **creación/sobrescritura** del costo por hora tenía el mismo patrón: solo verificaba el rol `approver`, y luego operaba sobre `request.employee_id` sin validar scope.

> Más grave que el GET porque permite no solo leer sino **modificar costos ajenos**. Un approver malintencionado podía, por ejemplo, sobrescribir el costo de un directivo a `$1/h` para distorsionar reportes financieros, o cerrar registros abiertos antes de tiempo.

Ambos endpoints son explotables por **cualquiera de los ~17 approvers del sistema** contra cualquier empleado, ergo configuran el riesgo real que describe VT-02.

#### Hallazgo bonus: enum de roles incorrecto en producción

Como side-finding al investigar los chequeos de rol, encontramos que `app/shared/security/roles.py` cae por defecto a `role_enums/dev.py` cuando no encuentra `prod.py` (que **no existe**). En producción, los IDs de rol no coinciden con los de Odoo prod, lo que puede hacer que `user_has_role(...Roles.approver)` falle silenciosamente. Se documenta como issue separado (no bloqueante para VT-02, porque el sistema valida con los IDs de dev y aun así estos endpoints eran vulnerables).

### Solución aplicada

Se introdujo un **helper de autorización a nivel de scope** reutilizable y se aplicó a los dos endpoints vulnerables. El criterio de scope:

- El solicitante puede operar sobre **su propio empleado** (self-access).
- O bien sobre cualquier `employee_id` que esté en la lista que devuelve `TimesheetLineGateway.get_team_users(...)` (subordinados directos + cadena descendente vía `child_of` de Odoo).
- En cualquier otro caso, **HTTP 403**.

**1) Helper reusable `app/shared/security/authorization.py`** (también lo aprovechamos al llegar a VT-16, mismo patrón):

```17:84:odoo-conector-be/app/shared/security/authorization.py
def ensure_employee_in_team(
    *,
    requester_user_id: int,
    target_employee_id: int,
    employee_gateway: EmployeeGateway,
    timesheet_gateway: TimesheetLineGateway,
) -> None:
    requester_employee = employee_gateway.get_by_id(requester_user_id)
    if requester_employee is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un empleado asociado en Odoo",
        )
    if target_employee_id == requester_employee.id:
        return
    team_users = timesheet_gateway.get_team_users(
        requester_user_id, requester_employee.id
    )
    team_ids = {member["id"] for member in team_users}
    if target_employee_id not in team_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para operar sobre este empleado",
        )
```

**2) Scope check en `GET /history/{employee_id}`** — se aplica **antes** del lookup en BD para evitar que la diferencia entre 403 (fuera de scope) y 404 (no existe) sirva para enumerar IDs válidos:

```111:160:odoo-conector-be/app/employee_price/api/routers.py
@router.get("/history/{employee_id}", response_model=list[EmployeePriceHistoryItem])
async def get_employee_price_history(
    employee_id: int,
    db: Session = Depends(get_db),
    timesheet_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: JWTPayload = Depends(get_current_user),
):
    ...
    if not is_approver:
        raise HTTPException(...)

    # Scope check (VT-02): ANTES de tocar la BD.
    ensure_employee_in_team(
        requester_user_id=current_user["user_id"],
        target_employee_id=employee_id,
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )
    ...
```

**3) Scope check en `POST /employees-price/`**:

```187:230:odoo-conector-be/app/employee_price/api/routers.py
@router.post("/", response_model=CreateEmployeePriceResponse)
async def create_employee_price(
    request: CreateEmployeePriceRequest,
    db: Session = Depends(get_db),
    timesheet_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: JWTPayload = Depends(get_current_user),
):
    ...
    if not is_approver:
        raise HTTPException(...)

    ensure_employee_in_team(
        requester_user_id=current_user["user_id"],
        target_employee_id=request.employee_id,
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )
    ...
```

**4) Tests de regresión IDOR.** Se agregaron 7 tests específicos en `app/employee_price/tests/integration/test_employee_price_routers.py` que validan:

- 403 al consultar history de un empleado fuera del equipo.
- 403 al intentar crear/actualizar precio de un empleado fuera del equipo.
- 403 cuando el solicitante no tiene `Employee` asociado en Odoo.
- 200 cuando el solicitante consulta/edita su propio precio (self-access).
- 403 idéntico para targets que existen y para targets inexistentes (no se filtra existencia vía response code).

Todos los tests preexistentes se adaptaron para mockear los gateways de equipo (33 tests pasando en el módulo).

### Verificación post-deploy

```bash
# Approver legítimo consultando un miembro de SU equipo:
curl -i https://geo-timesheet-be.soportegeonosis.com.ar/api/v1/employees-price/history/<member_id> \
  -H "Authorization: Bearer <token_approver>"
# → 200 OK + historial

# Mismo approver intentando consultar un empleado FUERA de su equipo:
curl -i https://geo-timesheet-be.soportegeonosis.com.ar/api/v1/employees-price/history/<random_id> \
  -H "Authorization: Bearer <token_approver>"
# → 403 Forbidden — "No tienes permisos para operar sobre este empleado"

# Intento de modificar el costo de un empleado fuera del equipo:
curl -i -X POST https://geo-timesheet-be.soportegeonosis.com.ar/api/v1/employees-price/ \
  -H "Authorization: Bearer <token_approver>" \
  -H "Content-Type: application/json" \
  -d '{"employee_id": <other_team_id>, "date_from":"2026-05-11", "cost_per_hour": 1}'
# → 403 Forbidden
```

Suite del módulo:

```bash
cd odoo-conector-be
pytest app/employee_price/tests/integration -q
# 33 passed
```

### Riesgos y regresiones evaluados

| Riesgo | Mitigación |
|---|---|
| Romper a managers legítimos que veían empleados fuera de su jerarquía | El criterio de scope replica exactamente la lógica que `GET /employees-price/` ya usaba (sin quejas reportadas). Si surge un caso de manager "transversal", se incorpora vía Odoo (`timesheet_manager_id` / `child_of`), no relajando el helper. |
| Latencia: cada request hace una llamada extra a Odoo (`get_team_users`) | Aceptable: ya pagábamos esa llamada en `GET /` sin problemas. Si se vuelve un cuello de botella, se cachea el resultado por user_id por unos segundos. |
| El helper devuelve 403 también para usuarios sin Employee asociado | Decisión consciente. Antes, un user sin Employee podía golpear estos endpoints; ahora queda bloqueado. Es estrictamente más seguro. |
| Que tests existentes asuman acceso libre | Se actualizaron los tests para mockear `get_team_users` y `OdooEmployeeGateway.get_by_id` con un "equipo amplio" por default, manteniendo la cobertura intacta. |
| Que el cambio de `404 → 403` en `GET /history/{id}` para IDs inexistentes rompa algún flujo | El frontend nunca consulta IDs random; siempre vienen de un listado previo (que ya está scoped). No hay regresión de UX. |

### Trabajo relacionado pendiente

- **Bug de roles en producción** (hallazgo bonus): falta `app/shared/security/role_enums/prod.py`. Se crea issue aparte para no mezclar.
- **VT-16** (IDOR en `/dashboard/summary/{employee_id}`): mismo patrón, mismo helper. Se aborda al llegar a VT-16 reusando `ensure_employee_in_team`.
- **VT-04 / VT-14** (IDORs sobre timesheets): patrón análogo pero con ownership por `timesheet_line.id`. Se aborda con un helper hermano (`ensure_owns_timesheet` o `ensure_timesheets_in_team`).
- **VT-08** (paginado y filtros del listado masivo): cierra el risco residual de "datos masivos legítimamente accesibles pero exportables a granel".
- **Auditoría/logging** de accesos rechazados con 403 en `employees-price/*`: actualmente caen al exception handler genérico. Sería deseable un log estructurado con `requester_user_id`, `target_employee_id`, ruta, IP — para detectar barridos. Out of scope de VT-02; se puede tomar como hardening posterior.
