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
| VT-02 | Fuga de tarifas salariales (`/employees-price/`) | 9.1 | ⏳ |
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
