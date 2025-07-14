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

**Fecha**: Marzo 2024  
**Autor**: Equipo de Desarrollo  
**Versión**: 1.0
