# Solución: Sistema de Equipos y Múltiples Aprobadores en Geotimeshift

## Contexto del problema

### Cómo funciona hoy

Geotimeshift determina el "equipo" de un usuario consultando Odoo en tiempo real con esta lógica (`get_team_users`):

- Empleados donde el `timesheet_manager_id` es el usuario logueado, **O**
- Empleados que son hijos jerárquicos del empleado logueado (`child_of` en el árbol de Odoo)

Esto significa que equipo = jerarquía de departamento en Odoo. No existen equipos cross-departamentales ni la figura de sublíder.

### Limitaciones actuales

| Limitación | Impacto |
|---|---|
| Solo un aprobador por empleado en Odoo (`timesheet_manager_id`) | Si el aprobador se ausenta, nadie puede validar |
| `timesheet_manager_id` requiere `res.users` en Odoo | Solo empleados con usuario Odoo pueden ser aprobadores |
| Crear usuarios Odoo tiene costo de licencia | No es viable escalar aprobadores comprando licencias |
| `action_validate_timesheet` verifica el UID del llamante | El usuario de servicio solo puede validar empleados donde es manager |
| `validate()` confía ciegamente en `bool(response)` | Falso positivo: el toast dice "validado" pero Odoo no hizo nada |

### Bug crítico existente

```python
# odoo_timesheet_gateway.py — línea 402
return bool(response)  # ← PROBLEMA: siempre True aunque Odoo no validó nada
```

Odoo retorna una `ir.actions.act_window` (dict no vacío) cuando falla la validación por permisos. `bool({...})` es `True`. El frontend muestra éxito, pero al refrescar las horas siguen en draft.

---

## Solución propuesta

La solución tiene tres componentes independientes que se pueden implementar en orden.

### Componente 1 — Módulo Odoo mínimo (campo `x_validated_by`)

**Qué hace:** Agrega un campo `x_validated_by` (Many2one a `hr.employee`) en `account.analytic.line` para registrar quién aprobó cada línea de timesheet.

**Por qué `hr.employee` y no `res.users`:**
- `hr.employee` existe para todos los empleados, tengan o no usuario Odoo
- El email ya está en `hr.employee.work_email` (misma fuente que usa geotimeshift)
- El módulo Proyectos puede leerlo directamente

**Código del módulo (solo el campo, sin lógica):**

```python
# geo_timesheet_approver/models/account_analytic_line.py
from odoo import fields, models

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    x_validated_by = fields.Many2one(
        "hr.employee",
        string="Aprobado por",
        readonly=True,
    )
```

**Estructura del módulo:**
```
geo_timesheet_approver/
├── __manifest__.py
├── __init__.py
└── models/
    ├── __init__.py
    └── account_analytic_line.py
```

Este módulo es intencionalmente mínimo. Toda la lógica de negocio vive en geotimeshift.

---

### Componente 2 — Configuración en Odoo (sin código)

**Qué hacer:** Darle al usuario de servicio (`ODOO_USERNAME`) el grupo **Timesheets Administrator** (`account.group_time_sheet_manager`).

**Dónde:** Odoo → Configuración → Usuarios → [usuario de servicio] → Hoja de horas: Administrador

**Por qué este grupo y no Administrador:**

| Grupo | Puede validar timesheets | Acceso al resto del ERP |
|---|---|---|
| Timesheets Administrator | ✅ | ❌ Solo timesheets |
| Administrador | ✅ | ✅ Todo (riesgo innecesario) |

Con `Timesheets Administrator`, el usuario de servicio puede ejecutar `action_validate_timesheet` sobre cualquier empleado sin restricciones, y el blast radius en caso de compromiso de credenciales queda acotado al módulo de timesheets.

---

### Componente 3 — Nuevo módulo `app/team/` en geotimeshift

#### Modelos de datos (nuevas tablas en la BD de geotimeshift)

```
Team
  id          UUID / serial
  name        string (único)
  description string (opcional)
  created_at  timestamp

TeamMember
  id                  UUID / serial
  team_id             FK → Team
  employee_odoo_id    integer  ← hr.employee.id en Odoo (NO res.users)
  role                enum: "leader" | "sub_leader" | "member"
  created_at          timestamp
```

**Punto clave:** `employee_odoo_id` apunta a `hr.employee.id`, no a `res.users`. Cualquier empleado sincronizado en geotimeshift puede ser líder o sublíder sin necesidad de usuario Odoo.

#### Endpoints nuevos (protegidos por rol admin)

```
POST   /api/v1/teams                → crear equipo
GET    /api/v1/teams                → listar todos los equipos con miembros
GET    /api/v1/teams/mine           → equipos donde el usuario logueado es leader/sub_leader
GET    /api/v1/teams/{id}           → detalle de un equipo
PUT    /api/v1/teams/{id}           → editar equipo (nombre, descripción, miembros, roles)
DELETE /api/v1/teams/{id}           → eliminar equipo
POST   /api/v1/teams/{id}/members   → agregar miembro
DELETE /api/v1/teams/{id}/members/{employee_id} → quitar miembro
```

#### Cambios en lógica existente

**`get_team_users` (modificación):**

```python
def get_team_users(self, user_id: int, employee_id: int):
    # 1. Buscar si el usuario es líder/sublíder en BD local
    team = team_member_repo.find_team_by_leader(employee_odoo_id=employee_id)
    if team:
        return team_member_repo.get_member_employee_ids(team.id)

    # 2. Fallback: comportamiento actual (jerarquía de Odoo)
    return odoo_query_subordinates(user_id, employee_id)
```

**`validate()` (fix del bug + registro del aprobador):**

```python
def validate(self, timesheet_line_ids: list[int], approved_by_employee_id: int) -> bool:
    if not timesheet_line_ids:
        return True

    # Ejecutar validación
    self.odoo_client["models"].execute_kw(
        ..., "account.analytic.line", "action_validate_timesheet",
        [timesheet_line_ids], {}
    )

    # Verificar que efectivamente quedaron validadas
    results = self.odoo_client["models"].execute_kw(
        ..., "account.analytic.line", "read",
        [timesheet_line_ids], {"fields": ["validated"]}
    )

    all_validated = all(r["validated"] for r in results)

    if all_validated:
        # Registrar quién aprobó
        self.odoo_client["models"].execute_kw(
            ..., "account.analytic.line", "write",
            [timesheet_line_ids, {"x_validated_by": approved_by_employee_id}]
        )

    return all_validated
```

**Guard de validación (modificación):**

```python
# En el endpoint POST /timesheet/validate
# Antes: solo chequea Roles.approver de Odoo
# Después: también acepta si es leader/sub_leader del equipo del empleado

def can_validate(current_user, target_employee_id):
    # Opción 1: es approver de Odoo (comportamiento legacy)
    if Roles.approver in current_user.roles:
        return True

    # Opción 2: es leader/sub_leader del equipo del empleado
    team = team_member_repo.find_team_by_leader(current_user.employee_odoo_id)
    if team and team_member_repo.is_member(team.id, target_employee_id):
        return True

    return False
```

---

## Flujo completo con la solución implementada

```
EMPLEADO carga horas en geotimeshift
  └─ Se escriben en Odoo (account.analytic.line, validated=False, x_validated_by=None)

LÍDER (con o sin usuario Odoo) abre geotimeshift
  └─ geotimeshift busca en TeamMember: ¿employee_odoo_id es leader/sub_leader?
  └─ Trae las horas de los employee_ids de su equipo desde Odoo

LÍDER valida las horas
  └─ geotimeshift verifica: ¿el empleado pertenece al equipo del líder? → OK
  └─ Llama a Odoo: action_validate_timesheet([ids]) con usuario de servicio (Timesheets Admin)
  └─ Escribe x_validated_by = leader_employee_id en Odoo
  └─ Lee validated=True para confirmar éxito real
  └─ Envía email al empleado

MÓDULO PROYECTOS en Odoo
  └─ Ve account.analytic.line con validated=True y x_validated_by=[nombre del líder]
```

---

## Tabla de roles y permisos

| Rol | Ve horas de | Puede validar | Requiere usuario Odoo |
|---|---|---|---|
| Empleado (member) | Solo las propias | No | No |
| Sublíder (sub_leader) | Miembros de su equipo | Sí, su equipo | No |
| Líder (leader) | Miembros de su equipo | Sí, su equipo | No |
| Aprobador legacy (rol Odoo) | Su equipo jerárquico Odoo | Sí, su jerarquía | Sí |
| Admin geotimeshift | Todos | Todos | No |

---

## Consideraciones de seguridad

### ¿Por qué NO usar el usuario Administrador de Odoo como usuario de servicio?

| Riesgo | Descripción |
|---|---|
| **Blast radius alto** | Si `ODOO_PASSWORD` se filtra, el atacante tiene acceso completo a Odoo (nóminas, facturación, configuración) |
| **Sin audit trail en Odoo** | Todo queda como "modificado por: api_service". El campo `x_validated_by` compensa esto para timesheets |
| **Escalación de privilegios** | Un bug de autorización en geotimeshift podría permitir operaciones fuera del scope de timesheets |

### Mitigación

- Usuario de servicio con **solo** `Timesheets Administrator` (no admin)
- Doble verificación: guard en geotimeshift + permisos en Odoo
- Campo `x_validated_by` para trazabilidad del aprobador real
- `validate()` confirma `validated=True` antes de considerar éxito

---

## Orden de implementación sugerido

1. **Fix del bug** — `validate()` verifica `validated=True` después de llamar a Odoo
2. **Módulo Odoo mínimo** — campo `x_validated_by` en `account.analytic.line`
3. **Configuración en Odoo** — rol `Timesheets Administrator` al usuario de servicio
4. **Migración Alembic** — tablas `Team` y `TeamMember` en geotimeshift
5. **CRUD de equipos** — endpoints protegidos por admin
6. **Modificar `get_team_users`** — buscar en BD local primero
7. **Modificar guard de validación** — aceptar leaders/sub_leaders de equipos
8. **`validate()` escribe `x_validated_by`** — una vez que el módulo Odoo está instalado

---

## Archivos a crear/modificar en geotimeshift

### Nuevos
```
app/team/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── routes.py
├── application/
│   ├── __init__.py
│   └── use_cases/
│       ├── create_team.py
│       ├── get_teams.py
│       ├── update_team.py
│       └── delete_team.py
├── domain/
│   ├── __init__.py
│   ├── models.py          ← Team, TeamMember, Role enum
│   └── repositories.py    ← TeamRepository interface
└── infra/
        ├── models.py       ← SQLAlchemy models
        └── repository.py   ← implementación
```

### Modificados
```
app/timesheet_line/infra/external/odoo/odoo_timesheet_gateway.py
  → validate(): verificar validated=True + escribir x_validated_by
  → get_team_users(): buscar en TeamMember primero

app/timesheet_line/api/routes.py (o donde esté el guard de validación)
  → can_validate(): aceptar leaders/sub_leaders
```├── __init__.py
    └── db/
        ├── __init__.py
    
