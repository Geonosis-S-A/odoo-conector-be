# Estructura Jerárquica del Dashboard

## Descripción General

Esta nueva funcionalidad implementa una estructura jerárquica anidada para el resumen del dashboard, reemplazando la estructura plana anterior de `by_project` y `by_task` con una representación que respeta la naturaleza jerárquica de proyectos → tareas → subtareas.

## Estructura de Datos

### HierarchicalItem

```python
@dataclass
class HierarchicalItem:
    type: str                      # "project" o "task"
    id: int                       # project_id para proyectos, task_id para tareas
    name: str                     # Nombre descriptivo
    total_hours: float            # Total de horas acumuladas
    total_entries: int            # Total de entradas/registros
    data: List[HierarchicalItem]  # Elementos hijos (anidados)
    is_artificial: bool = False   # Flag que indica si es un elemento artificial
```

### HierarchicalSummary

```python
@dataclass
class HierarchicalSummary:
    total_hours: float            # Total global de horas
    total_entries: int            # Total global de entradas
    data: List[HierarchicalItem]  # Lista de proyectos con estructura anidada
```

## Casos Borde Manejados

### 1. Horas Cargadas Directamente a Proyectos

**Problema**: Existen registros de tiempo cargados directamente a un proyecto sin asignar a una tarea específica.

**Solución**: Se genera automáticamente una tarea artificial con:

- `name`: "Sin tarea"
- `is_artificial`: `True`
- `id`: Número negativo único (comenzando desde -1000)
- Acumula todas las horas y entradas sin tarea para ese proyecto

### 2. Horas Cargadas a Tareas Padre Sin Subtareas

**Problema**: Existen registros de tiempo cargados directamente a una tarea padre, además de las horas de sus subtareas.

**Solución**: Se genera automáticamente una subtarea artificial con:

- `name`: "Sin subtarea"
- `is_artificial`: `True`
- `id`: Número negativo único (comenzando desde -2000)
- Contiene solo las horas cargadas directamente a la tarea padre

### 3. Tareas Sin Subtareas

**Problema**: Tareas que no tienen subtareas pero sí tienen horas registradas.

**Solución**: Se crea una subtarea artificial "Sin subtarea" que contiene todas las horas de la tarea.

## Algoritmo de Construcción

1. **Agrupación inicial**: Se agrupan todas las líneas de timesheet por proyecto
2. **Identificación de relaciones**: Se consultan los `parent_id` de todas las tareas para identificar jerarquías
3. **Cálculo de horas directas**:
   - Por proyecto: `horas_proyecto_total - suma_horas_todas_las_tareas`
   - Por tarea padre: `horas_tarea_total - suma_horas_subtareas`
4. **Generación de elementos artificiales**: Se crean tareas/subtareas artificiales para horas sin asignación específica
5. **Construcción de jerarquía**: Se construye la estructura anidada respetando las relaciones padre-hijo
6. **Ordenamiento**: Se ordenan los elementos por horas (mayor a menor) en cada nivel

## Identificación de Elementos Artificiales

### IDs Negativos

- **Tareas artificiales "Sin tarea"**: IDs desde -1000 hacia abajo
- **Subtareas artificiales "Sin subtarea"**: IDs desde -2000 hacia abajo

### Flag is_artificial

- `True`: Elemento generado automáticamente por el sistema
- `False`: Elemento real existente en Odoo

## Ejemplo de Estructura

```json
{
  "hierarchical_summary": {
    "total_hours": 10,
    "total_entries": 2,
    "data": [
      {
        "type": "project",
        "id": 1,
        "name": "Project 1",
        "total_hours": 8,
        "total_entries": 2,
        "is_artificial": false,
        "data": [
          {
            "type": "task",
            "id": 1,
            "name": "Tarea Principal",
            "total_hours": 6,
            "total_entries": 2,
            "is_artificial": false,
            "project_id": 1,
            "data": [
              {
                "type": "task",
                "id": 3,
                "name": "Subtarea 1",
                "total_hours": 5,
                "total_entries": 1,
                "is_artificial": false,
                "data": []
              },
              {
                "type": "task",
                "id": -2001,
                "name": "Sin subtarea",
                "total_hours": 1,
                "total_entries": 1,
                "is_artificial": true,
                "data": []
              }
            ]
          },
          {
            "type": "task",
            "id": 2,
            "name": "Tarea Simple",
            "total_hours": 2,
            "total_entries": 1,
            "is_artificial": false,
            "project_id": 1,
            "data": [
              {
                "type": "task",
                "id": -2002,
                "name": "Sin subtarea",
                "total_hours": 2,
                "total_entries": 1,
                "is_artificial": true,
                "data": []
              }
            ]
          }
        ]
      },
      {
        "type": "project",
        "id": 92,
        "name": "Project 2",
        "total_hours": 2,
        "total_entries": 1,
        "is_artificial": false,
        "data": [
          {
            "type": "task",
            "id": -1001,
            "name": "Sin tarea",
            "total_hours": 2,
            "total_entries": 1,
            "is_artificial": true,
            "project_id": 92,
            "data": []
          }
        ]
      }
    ]
  }
}
```

## Implementación

### Archivos Modificados

1. **`app/dashboard/domain/models.py`**

   - Agregados: `HierarchicalItem`, `HierarchicalSummary`
   - Modificado: `DashboardSummary.create()` para incluir `hierarchical_summary`

2. **`app/dashboard/domain/repositories.py`**

   - Agregado: `calculate_hierarchical_summary()` método abstracto

3. **`app/dashboard/infra/dashboard_service.py`**

   - Implementado: `calculate_hierarchical_summary()` y `_build_task_item()`

4. **`app/dashboard/application/use_cases/get_dashboard_summary.py`**

   - Modificado: Para calcular y incluir la estructura jerárquica

5. **`app/dashboard/api/schemas.py`**
   - Agregados: `HierarchicalItemResponse`, `HierarchicalSummaryResponse`
   - Modificado: `DashboardSummaryResponse` para incluir `hierarchical_summary`

### Compatibilidad

La nueva funcionalidad es **completamente compatible con la estructura anterior**:

- Los campos `totals.by_project` y `totals.by_task` se mantienen intactos
- La nueva estructura se agrega como campo opcional `hierarchical_summary`
- Los clientes pueden migrar gradualmente a usar la nueva estructura

## Ventajas

1. **Representación fiel**: Respeta la jerarquía real de proyectos y tareas
2. **Casos borde cubiertos**: Maneja automáticamente horas sin asignación específica
3. **Identificación clara**: Los elementos artificiales están claramente marcados
4. **Ordenamiento lógico**: Estructura ordenada por relevancia (horas)
5. **Compatibilidad**: No rompe la funcionalidad existente
6. **Escalabilidad**: Soporta jerarquías de cualquier profundidad

## Testing

Incluye script de prueba: `test_hierarchical_structure.py` que simula diferentes escenarios y valida la lógica de construcción de la estructura jerárquica.
