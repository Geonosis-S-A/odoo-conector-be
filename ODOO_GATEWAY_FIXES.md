# Documentación: Correcciones en Odoo Gateway y Tests

## 📋 Resumen

Este documento explica las correcciones implementadas en el gateway de Odoo y los tests de integración para manejar correctamente el comportamiento de los campos relacionales (Many2one) de Odoo.

## 🐛 Problema Original

### Error Principal

```
TypeError: 'bool' object is not subscriptable
```

### Ubicación del Error

- **Archivo**: `app/timesheet_line/infra/external/odoo/odoo_timesheet_gateway.py`
- **Líneas**: 25, 26, 71 (métodos `_transform_odoo_to_domain` y `_transform_odoo_to_detailed_domain`)

### Código Problemático

```python
# ❌ CÓDIGO QUE FALLABA:
employee_id = odoo_data.get("employee_id", [0, ""])[0]
project_id = odoo_data.get("project_id", [0, ""])[0]
task_id = odoo_data.get("task_id", [0, ""])[0] if odoo_data.get("task_id") else None
```

## 🔍 Causa Raíz

### Comportamiento de Odoo con Campos Many2one

Odoo maneja los campos relacionales (Many2one) de la siguiente manera:

| Situación           | Valor Devuelto | Ejemplo                 |
| ------------------- | -------------- | ----------------------- |
| **Campo con valor** | `[id, nombre]` | `[5, "María González"]` |
| **Campo vacío**     | `False`        | `False`                 |

### Casos de Negocio Donde Ocurre

1. **Timesheet sin tarea asignada**

   ```python
   {
       "employee_id": [5, "María González"],
       "project_id": [10, "Desarrollo Web"],
       "task_id": False  # ← No hay tarea específica
   }
   ```

2. **Empleado temporal o externo**

   ```python
   {
       "employee_id": False,  # ← Consultor externo
       "project_id": [15, "Proyecto Seguridad"],
       "task_id": [89, "Auditoría"]
   }
   ```

3. **Proyecto en configuración inicial**
   ```python
   {
       "employee_id": False,  # ← Aún no asignado
       "project_id": [20, "Nuevo Proyecto"],
       "task_id": False
   }
   ```

## ✅ Solución Implementada

### Código Corregido

```python
# ✅ CÓDIGO SOLUCIONADO:

# Manejar employee_id que puede ser False o [id, nombre]
employee_id = 0
raw_employee_id = odoo_data.get("employee_id", False)
if isinstance(raw_employee_id, list) and len(raw_employee_id) > 0:
    employee_id = raw_employee_id[0]
elif isinstance(raw_employee_id, (int, str)):
    employee_id = int(raw_employee_id)

# Manejar project_id que puede ser False o [id, nombre]
project_id = 0
raw_project_id = odoo_data.get("project_id", False)
if isinstance(raw_project_id, list) and len(raw_project_id) > 0:
    project_id = raw_project_id[0]
elif isinstance(raw_project_id, (int, str)):
    project_id = int(raw_project_id)

# Manejar task_id
task_id: int | None = None
raw_task_id = odoo_data.get("task_id")
if isinstance(raw_task_id, list) and len(raw_task_id) > 0:
    task_id = raw_task_id[0]
elif isinstance(raw_task_id, (int, str)):
    task_id = int(raw_task_id)
```

### Lógica de Manejo

La solución implementa una verificación robusta que maneja todos los casos posibles:

1. **Verificación de tipo**: `isinstance(raw_value, list)`
2. **Verificación de contenido**: `len(raw_value) > 0`
3. **Extracción segura**: `raw_value[0]`
4. **Casos edge**: Manejo de IDs como int o string
5. **Valor por defecto**: `0` para IDs, `None` para campos opcionales

## 🧪 Correcciones en Tests

### Problemas Identificados y Solucionados

#### 1. **Employee ID Inexistente**

```python
# ❌ ANTES: Usaba employee_id=2 (no existe)
"employee_id": 2

# ✅ DESPUÉS: Usa employee_id=1 (existe en Odoo)
"employee_id": 1
```

#### 2. **URLs Incorrectas**

```python
# ❌ ANTES: URLs sin prefijo API
"/timesheet/"

# ✅ DESPUÉS: URLs con prefijo correcto
"/api/v1/timesheet/"
```

#### 3. **Fixture de Test Client**

```python
# ✅ AGREGADO: Fixture para test client
@pytest.fixture
def test_client():
    return TestClient(app)
```

#### 4. **Método de Cleanup**

```python
# ❌ ANTES: Parámetro incorrecto
repository.delete(line.id)

# ✅ DESPUÉS: Lista de IDs como espera Odoo
repository.delete([line.id])
```

## 📊 Resultados

### Antes de las Correcciones

- ❌ 25 tests de integración fallando
- ❌ TypeError en transformación de datos
- ❌ URLs incorrectas en tests
- ❌ Employee IDs inexistentes

### Después de las Correcciones

- ✅ 30 tests unitarios: **TODOS PASANDO**
- ✅ 25 tests de integración: **TODOS PASANDO**
- ✅ **Total: 55 tests funcionando correctamente**

## 🛠️ Archivos Modificados

### 1. Gateway Principal

- **Archivo**: `app/timesheet_line/infra/external/odoo/odoo_timesheet_gateway.py`
- **Cambios**: Métodos `_transform_odoo_to_domain` y `_transform_odoo_to_detailed_domain`

### 2. Tests de Integración

- **Archivo**: `app/timesheet_line/tests/integration/test_timesheet_integration.py`
- **Cambios**: URLs, employee IDs, fixtures

### 3. Tests de Repository

- **Archivo**: `app/timesheet_line/tests/integration/test_odoo_repository.py`
- **Cambios**: Employee IDs, método de cleanup

## 🔧 Guía para Desarrolladores

### Trabajando con Campos Many2one de Odoo

**✅ HACER:**

```python
# Siempre verificar el tipo antes de acceder
raw_field = odoo_data.get("field_name", False)
if isinstance(raw_field, list) and len(raw_field) > 0:
    field_id = raw_field[0]
    field_name = raw_field[1] if len(raw_field) > 1 else ""
```

**❌ NO HACER:**

```python
# Nunca asumir que siempre será una lista
field_id = odoo_data.get("field_name", [0, ""])[0]  # ← Puede fallar
```

### Casos de Uso Comunes

```python
# Patrón para campos obligatorios (employee_id, project_id)
field_id = 0
raw_field = odoo_data.get("field_name", False)
if isinstance(raw_field, list) and len(raw_field) > 0:
    field_id = raw_field[0]
elif isinstance(raw_field, (int, str)):
    field_id = int(raw_field)

# Patrón para campos opcionales (task_id)
field_id = None
raw_field = odoo_data.get("field_name")
if isinstance(raw_field, list) and len(raw_field) > 0:
    field_id = raw_field[0]
elif isinstance(raw_field, (int, str)):
    field_id = int(raw_field)
```

## 📝 Tests

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Solo tests de integración
pytest -m integration

# Solo tests unitarios
pytest -m "not integration"

# Tests específicos del gateway
pytest app/timesheet_line/tests/integration/test_odoo_repository.py
```

### Verificar Cobertura

```bash
# Los tests ahora cubren:
# - Campos Many2one con valores
# - Campos Many2one vacíos (False)
# - Casos edge con IDs como string/int
# - Operaciones CRUD completas
# - Filtros por empleado y fechas
```

## 🚨 Puntos Importantes

### Para Nuevos Desarrolladores

1. **Siempre verificar tipos**: Odoo puede devolver `False`, `[id, nombre]`, o casos edge
2. **No asumir formatos**: Los datos pueden venir en diferentes formatos según el contexto
3. **Usar employee_id=1 en tests**: Es el único empleado garantizado en el sistema de pruebas
4. **URLs completas en tests**: Siempre usar `/api/v1/` como prefijo

### Para Debugging

```python
# Agregar logs para debugging
print(f"Raw data: {odoo_data}")
print(f"Employee ID raw: {odoo_data.get('employee_id')}")
print(f"Type: {type(odoo_data.get('employee_id'))}")
```

## 📚 Referencias

- [Documentación oficial de Odoo - Many2one fields](https://www.odoo.com/documentation/16.0/developer/reference/backend/orm.html#many2one)
- [Odoo XML-RPC API](https://www.odoo.com/documentation/16.0/developer/misc/api/xmlrpc.html)

---

# Equipos y permisos de timesheet (GEO-953) — "Opción 2"

> Branch: `feature/geo-953-teams-timesheet-approver`. Reemplaza el modelo previo de equipos administrados en Geo.

## 🎯 Qué se hizo y por qué

Odoo solo permite **un aprobador por empleado**. Se necesitaba que líderes/PMs y algunos miembros pudieran **ver** y **validar** las horas de su equipo, sin montar un roster paralelo que se desincronice de Odoo.

**Decisión (Opción 2):** el equipo **no se administra en Geo**. El equipo de un líder es **siempre la jerarquía de Odoo en vivo** (`get_team_users`: empleados con `timesheet_manager_id == user` o `child_of` en el organigrama, excluyendo al líder). Lo único que Geo persiste es un **permiso por par (líder, miembro)** con un nivel.

Si Odoo mueve a alguien de área, deja de aparecer en el equipo y su permiso **deja de aplicar automáticamente**, sin que nadie toque nada.

### Estados de permiso (por persona)

| `level`            | Qué puede hacer esa persona            |
| ------------------ | ------------------------------------- |
| `null` (sin fila)  | Solo ve **sus propias** horas         |
| `"view"`           | Ve las horas de **todo el equipo**    |
| `"validate"`       | **Ve y valida** las horas del equipo  |

El **líder de Odoo** siempre tiene ver + validar sobre su equipo, sin necesidad de fila.

## 🔐 Reglas de seguridad

Toda aprobación se ejecuta en Odoo con el **usuario de servicio**, así que el chequeo de permisos es crítico:

1. **Líder de Odoo** → ve y valida su equipo siempre (se re-deriva en vivo, nunca cacheado entre requests).
2. **Miembro con `validate`** → puede ver/validar **solo** al equipo Odoo de ese líder, **excluyendo al propio líder y a sí mismo**. Nunca hay auto-aprobación ni aprobación "hacia arriba".
3. Si el miembro tiene filas de varios líderes → se **unen** los equipos, con la misma exclusión.
4. Al fijar un permiso (`PUT`) se valida que la persona esté **hoy** en el equipo Odoo de ese líder → `400` si no.
5. En cada `POST /timesheet/validate` se re-deriva el equipo del líder en vivo desde Odoo y se verifica que **cada** línea pertenezca a un empleado permitido → `422` si alguna queda fuera.
6. En las rutas `/teams/mine`, la identidad del líder sale del **JWT**; el cliente nunca manda el id del líder.

## 🗄️ Cambios de modelo (reemplazo, no acumulación)

**Eliminado:** tablas `teammodel` / `teammembermodel`, roles `leader/pm/sub_leader/member`, CRUD admin de `/teams` (`create/update/delete/get_teams`).

**Nuevo:** tabla única `teammemberpermissionmodel`

| Columna                    | Tipo   | Notas                              |
| -------------------------- | ------ | ---------------------------------- |
| `id`                       | int PK |                                   |
| `leader_employee_odoo_id`  | int    | indexado                          |
| `member_employee_odoo_id`  | int    | indexado                          |
| `level`                    | str    | `CHECK IN ('view','validate')`    |
| `created_at`               | datetime |                                 |
| —                          | —      | `UNIQUE(leader, member)`          |

Migración: `migrations/versions/f1a2b3c4d5e6_add_team_member_permission_table.py` (head única).

## 🛠️ Archivos tocados

| Archivo | Cambio |
| ------- | ------ |
| `app/team/domain/models.py` | `PermissionLevel`, `TeamMemberPermission` |
| `app/team/domain/repositories.py` | `TeamPermissionRepository` |
| `app/team/infra/db/models.py` · `.../repositories.py` | `TeamMemberPermissionModel` + repo SQLModel |
| `app/team/application/team_access.py` | **`TeamAccessService`**: resuelve equipo Odoo en vivo + cruce con permisos (`visible_employee_ids`, `validatable_employee_ids`, `can_view_team`, `can_validate_team`) |
| `app/team/application/use_cases/get_team.py` · `set_member_permission.py` | casos de uso nuevos |
| `app/team/api/routes.py` · `schemas.py` · `dependencies.py` | endpoints nuevos (ver spec) |
| `app/timesheet_line/application/use_cases/obtener_horas.py` · `validar_timesheet.py` | usan `TeamAccessService` en vez del repo viejo |
| `app/timesheet_line/api/routers.py` | chequeos de permiso de no-admin vía `TeamAccessService` |
| `app/timesheet_line/infra/external/odoo/odoo_timesheet_gateway.py` | `all()`: la vista de equipo ahora se acota **siempre** a la lista explícita de empleados (antes, sin `user_id`, devolvía *todo* — bug latente) |
| `migrations/env.py` | import del modelo nuevo |

Tests nuevos: `app/team/tests/unit/` + casos de scoping en `app/timesheet_line/tests/unit/test_validate_timesheet.py`.

---

## 📱 Spec para el Front

Base URL: `/api/v1`. Todas las llamadas con el **Bearer token** actual (mismo auth que el resto).

### Modelo mental

- El equipo **no se administra**: es la jerarquía de Odoo en vivo.
- Lo único editable es el **permiso por persona** (`null` / `"view"` / `"validate"`).

### 0. `GET /teams/my-access` — gating del front (llamar al cargar la app)

Una sola llamada que dice qué puede hacer el usuario logueado con "su equipo".
Sirve para decidir qué menús / pantallas / botones mostrar, incluido el
estado **intermedio** (ver el equipo sin poder aprobar).

**200** (siempre 200, incluso sin acceso)
```json
{
  "is_leader": false,
  "can_view_team": true,
  "can_validate_team": false,
  "members": [
    { "employee_odoo_id": 101, "name": "Ana Pérez", "email": "ana@x.com" },
    { "employee_odoo_id": 102, "name": "Beto Ruiz", "email": null }
  ]
}
```

`members` = los empleados cuyas horas puede VER (equipo propio si lidera, o la
unión de los equipos de sus líderes otorgantes, sin el líder ni él mismo).

| Respuesta | UI |
| --------- | -- |
| `can_view_team: false` | Sin sección de equipo. Solo sus horas. |
| `can_view_team: true` + `can_validate_team: false` | **Intermedio**: pantalla de equipo listando `members` + sus horas (`GET /timesheet/?team=true`), **sin botón Validar**. |
| `can_validate_team: true` (o `is_leader: true`) | Igual + botón **Validar**. |
| `is_leader: true` | Además, mostrar la pantalla de administración de permisos (`GET /teams/mine`). |

### 1. `GET /teams/mine` — pantalla del líder

Trae el equipo del usuario logueado (según Odoo) + el permiso actual de cada uno.

**200**
```json
{
  "leader_employee_odoo_id": 42,
  "members": [
    { "employee_odoo_id": 101, "name": "Ana Pérez", "email": "ana@x.com", "level": "validate" },
    { "employee_odoo_id": 102, "name": "Beto Ruiz", "email": "beto@x.com", "level": "view" },
    { "employee_odoo_id": 103, "name": "Cira Díaz", "email": null,          "level": null }
  ]
}
```

- **403** → el usuario **no lidera ningún equipo en Odoo**. El front **oculta** la sección de equipos/permisos. (Sirve de "¿muestro la pantalla?": 200 = sí, 403 = no.)
- `email` y `level` pueden venir `null`.

### 2. `PUT /teams/mine/members/{employee_odoo_id}` — botón de permiso

`{employee_odoo_id}` = el del miembro (viene en `members[]`).

**Body**
```json
{ "level": "view" }   // "view" | "validate" | "none"
```
- `"view"` → "solo ver a los demás"
- `"validate"` → "ver y aprobar"
- `"none"` → quitar el permiso (vuelve a ver solo sus horas)

**200** — el miembro con su estado ya actualizado:
```json
{ "employee_odoo_id": 102, "name": "Beto Ruiz", "email": "beto@x.com", "level": "validate" }
```

- **400** → la persona ya no está en el equipo del líder en Odoo. Mostrar aviso y refetch `GET /teams/mine`.
- **403** → dejó de ser líder. Ocultar la sección.

**UI sugerida por fila:** control de 3 opciones **Sin acceso · Ver equipo · Ver y aprobar** → `none` / `view` / `validate`. Al cambiar, `PUT` con ese `level` y aplicar la respuesta a la fila (no hace falta refetch salvo 400).

### 3. Endpoints admin (rol `approver`) — opcional

Mismos contratos, pasando el id del líder en la ruta:

- `GET /teams/{leader_employee_odoo_id}` → como `/mine` pero de cualquier líder. **404** si ese empleado no lidera equipo en Odoo. **403** si no es admin.
- `PUT /teams/{leader_employee_odoo_id}/members/{member_employee_odoo_id}` → body idéntico.

### 4. Timesheet — qué cambió para el consumidor

Los endpoints **no cambian de forma**; cambia quién tiene permiso.

- `GET /timesheet/?team=true&date_from=...&date_to=...`
  - Funciona para: admins, líderes de Odoo, y miembros con `level` `view` **o** `validate`.
  - **403** si no aplica → no ofrecer la vista "equipo" a ese usuario.
  - Para un miembro no incluye las horas del líder.
- `POST /timesheet/validate` (body actual: `{ "timesheetline_ids": [...], "approver_mail": "..." }`)
  - Permitido para: admins, líderes de Odoo, y miembros con `level: "validate"`.
  - **403** si no tiene ese permiso.
  - **422** (`"...fuera de tu equipo..."`) si intenta validar horas de alguien fuera de su alcance o propias. Prevenirlo deshabilitando esas filas en la selección.

### Cómo decidir qué mostrar

Usar **`GET /teams/my-access`** (sección 0) al cargar la app. Con esa única
respuesta el front decide todo:

| `my-access` | UI |
| ----------- | -- |
| `can_view_team: false` | Nada de equipo. |
| `can_view_team: true`, `can_validate_team: false` | Vista de equipo (lista `members` + `GET /timesheet/?team=true`), **sin** botón Validar. |
| `can_validate_team: true` | Vista de equipo **con** botón Validar (`POST /timesheet/validate`). |
| `is_leader: true` | Además, pantalla de permisos (`GET /teams/mine` + `PUT`). |

### Errores — resumen

| Código | Significado | Acción del front |
| ------ | ----------- | ---------------- |
| 401 | Token inválido/expirado | Re-login |
| 403 en `/teams/mine` | No lidera equipo | Ocultar sección |
| 403 en `/teams/{leaderId}` | No es admin | Ocultar vista admin |
| 400 en `PUT .../members/...` | Persona fuera del equipo Odoo | Aviso + refetch `/teams/mine` |
| 403 en `/timesheet/...` | Sin permiso de equipo/validación | Ocultar acción |
| 422 en `/timesheet/validate` | Líneas fuera de alcance | Bloquear selección de esas filas |

### Migración desde la API vieja

La API previa de equipos (`POST/GET/PUT/DELETE /teams`, `/teams/{id}/members`, roles `leader/pm/sub_leader/member`) **fue eliminada**. Reemplazar todo el consumo por `/teams/mine` (+ `/teams/{leaderId}` para la vista admin).

## ⏳ YA ESTA DESARROLLADO EN ODOO

- Módulo Odoo `geo_timesheet_approver/` con campo `x_validated_by` en `account.analytic.line`.

## FALTA IMPLEMENTAR 

- Rol *Timesheets Administrator* al usuario de servicio en Odoo.

---

**Fecha**: Marzo 2024 (Many2one) · Septiembre 2026 (Equipos GEO-953)  
**Autor**: Equipo de Desarrollo  
**Versión**: 2.0
