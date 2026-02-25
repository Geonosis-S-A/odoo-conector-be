from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
import json
from datetime import date, datetime
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.project.infra.external.odd_project_gateway import OdooProjectGateway
from app.project.application.use_cases.obtener_proyectos import ObtenerProyectosUseCase
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from rapidfuzz import process, fuzz

from app.task.application.use_cases.obtener_tareas import ObtenerTareasUseCase
from app.task.domain.gateway import TaskGateway
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.task.domain.models import Task
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway

# Imports para timesheet
from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.timesheet_line.application.excepctions.exceptions import (
    InvalidHoursError,
    TimesheetCreationError,
    TimesheetNotFoundError,
)


# ============================================================================
# FUNCIONES AUXILIARES PARA PROCESAMIENTO DE TAREAS
# ============================================================================


def _task_to_dict(task):
    """Transforma un objeto Task a diccionario de forma recursiva."""
    return {
        "id": task.id,
        "name": task.name,
        "state": task.state,
        "subtasks": [_task_to_dict(subtask) for subtask in task.subtask]
        if task.subtask
        else [],
    }


def _flatten_tasks(tasks_list, parent_path="", depth=0):
    """Aplana tareas jerárquicas, retornando solo las tareas finales (sin subtareas) con nombres completos.

    Args:
        tasks_list: Lista de tareas en formato diccionario
        parent_path: Ruta acumulada de ancestros (ej: "Padre → Hijo")
        depth: Profundidad actual de recursión (protección contra loops infinitos)

    Returns:
        Lista de tareas aplanadas con nombres jerárquicos completos
    """
    flattened = []

    # Protección contra recursión infinita (límite de 10 niveles)
    if depth > 10:
        return flattened

    for task in tasks_list:
        # Construir el nombre completo con la ruta completa de ancestros
        full_name = f"{parent_path} → {task['name']}" if parent_path else task["name"]

        # Si la tarea no tiene subtareas, la agregamos al resultado final
        if not task["subtasks"] or len(task["subtasks"]) == 0:
            flattened.append(
                {"id": task["id"], "name": full_name, "state": task["state"]}
            )
        else:
            # Si tiene subtareas, procesamos recursivamente cada subtarea
            # NO agregamos la tarea padre al resultado, solo sus descendientes
            nested_results = _flatten_tasks(task["subtasks"], full_name, depth + 1)
            flattened.extend(nested_results)

    return flattened


# ============================================================================
# HERRAMIENTAS DEL AGENTE
# ============================================================================


@tool
def search_project_by_name(name: str) -> str:
    """Search a project by name using fuzzy matching. Returns a list of projects that match the name.

    Args:
        name: The project name to search for
        threshold: Minimum similarity score (0-100). Default is 60.
    """
    try:
        threshold: int = 20
        # Obtener la conexión a Odoo
        odoo_connection = get_odoo_connection()

        # Crear el gateway y el use case
        gateway = OdooProjectGateway(odoo_connection)
        use_case = ObtenerProyectosUseCase(gateway)

        # Obtener todos los proyectos
        projects = use_case.execute()

        if not projects:
            return "No hay proyectos disponibles."

        # Convertir proyectos a formato diccionario
        projects_list = [
            {"id": project.id, "name": project.name} for project in projects
        ]

        # Usar fuzzy matching para encontrar coincidencias
        # Normalizar a minúsculas para comparación insensible a mayúsculas
        choices = [p["name"].lower() for p in projects_list]
        matches = process.extract(
            name.lower(),
            choices,
            scorer=fuzz.WRatio,  # Muy bueno para búsquedas generales
            limit=10,
        )

        # Filtrar por threshold y agregar score
        matching_projects = []
        for matched_name, score, idx in matches:
            if score >= threshold:
                matching_projects.append(
                    {
                        "id": projects_list[idx]["id"],
                        "name": projects_list[idx]["name"],
                        "similarity_score": score,
                    }
                )

        if not matching_projects:
            return f"No se encontraron proyectos similares a '{name}' (umbral de similitud: {threshold}%)."

        # Retornar como JSON para que el agente pueda procesarlo mejor
        return json.dumps(
            {
                "search_term": name,
                "found": len(matching_projects),
                "projects": matching_projects,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return f"Error al buscar proyectos: {str(e)}"


@tool
def get_all_projects() -> str:
    """Get all available projects from Odoo."""
    try:
        # Obtener la conexión a Odoo
        odoo_connection = get_odoo_connection()

        # Crear el gateway y el use case
        gateway = OdooProjectGateway(odoo_connection)
        use_case = ObtenerProyectosUseCase(gateway)

        # Obtener todos los proyectos
        projects = use_case.execute()

        if not projects:
            return "No hay proyectos disponibles."

        # Retornar como JSON
        projects_list = [
            {"id": project.id, "name": project.name} for project in projects
        ]

        return json.dumps(
            {"total": len(projects_list), "projects": projects_list}, ensure_ascii=False
        )

    except Exception as e:
        return f"Error al obtener proyectos: {str(e)}"


@tool
def get_all_tasks_in_project(project_id: int) -> str:
    """Get all tasks in a specific project. Returns flattened tasks (only leaf tasks without subtasks) with full hierarchical names."""
    try:
        # Obtener la conexión a Odoo
        odoo_connection = get_odoo_connection()

        task_gateway = OdooTaskGateway(odoo_connection)
        use_case = ObtenerTareasUseCase(
            task_gateway,
            OdooTaskGateway(odoo_connection),
            OdooEmployeeGateway(odoo_connection),
        )
        tasks = use_case.execute(project_id)

        if not tasks:
            return f"No se encontraron tareas para el proyecto con ID {project_id}."

        # Transformar objetos Task a diccionarios
        transformed_tasks = [_task_to_dict(task) for task in tasks]

        # Aplanar las tareas
        flattened_tasks = _flatten_tasks(transformed_tasks)

        return json.dumps(
            {
                "project_id": project_id,
                "total_tasks": len(flattened_tasks),
                "tasks": flattened_tasks,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return f"Error al obtener tareas del proyecto {project_id}: {str(e)}"


@tool
def search_task_in_project(project_id: int, task_name: str) -> str:
    """Search a task in a project by name using fuzzy matching. Searches in flattened tasks (only leaf tasks) with full hierarchical names.

    Args:
        project_id: The ID of the project to search in
        task_name: The task name to search for
        threshold: Minimum similarity score (0-100). Default is 20.
    """
    try:
        threshold: int = 20
        # Obtener la conexión a Odoo
        odoo_connection = get_odoo_connection()

        # Crear el gateway de tareas
        task_gateway = OdooTaskGateway(odoo_connection)
        use_case = ObtenerTareasUseCase(
            task_gateway,
            OdooTaskGateway(odoo_connection),
            OdooEmployeeGateway(odoo_connection),
        )

        # Obtener todas las tareas del proyecto
        tasks = use_case.execute(project_id)

        if not tasks:
            return f"No se encontraron tareas en el proyecto con ID {project_id}."

        # Transformar objetos Task a diccionarios
        transformed_tasks = [_task_to_dict(task) for task in tasks]

        # Obtener todas las tareas aplanadas
        all_tasks = _flatten_tasks(transformed_tasks)

        # Usar fuzzy matching para encontrar coincidencias
        # Normalizar a minúsculas para comparación insensible a mayúsculas
        choices = [t["name"].lower() for t in all_tasks]
        matches = process.extract(
            task_name.lower(),
            choices,
            scorer=fuzz.WRatio,  # Muy bueno para búsquedas generales
            limit=10,
        )

        # Filtrar por threshold y agregar score
        matching_tasks = []
        for matched_name, score, idx in matches:
            if score >= threshold:
                task_match = all_tasks[idx].copy()
                task_match["similarity_score"] = score
                matching_tasks.append(task_match)

        if not matching_tasks:
            return f"No se encontraron tareas similares a '{task_name}' en el proyecto {project_id} (umbral de similitud: {threshold}%)."

        return json.dumps(
            {
                "project_id": project_id,
                "search_term": task_name,
                "found": len(matching_tasks),
                "tasks": matching_tasks,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return f"Error al buscar tareas en el proyecto {project_id}: {str(e)}"


@dataclass
class Context:
    """Custom runtime context schema."""

    employee_id: int


def _parse_date(date_str: str) -> date:
    """Parsea una fecha desde string a objeto date.

    Args:
        date_str: Fecha como string (YYYY-MM-DD, DD/MM/YYYY, "hoy", "today")

    Returns:
        date: Objeto date parseado

    Raises:
        ValueError: Si el formato de fecha es inválido
    """
    if date_str.lower() in ["hoy", "today"]:
        return date.today()

    # Intentar formato ISO (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Intentar formato español (DD/MM/YYYY)
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(
            f"Formato de fecha inválido: '{date_str}'. Usa YYYY-MM-DD (ej: 2024-11-14)"
        )


def _timesheet_line_to_dict(line) -> dict:
    """Convierte un DetailedTimesheetLine a diccionario para serialización JSON."""
    result = {
        "id": line.id,
        "employee_id": line.employee_id,
        "project_id": line.project.id,
        "project_name": line.project.name,
        "hours": line.hours,
        "date": line.date.isoformat(),
        "description": line.name if line.name else "Sin descripción",
        "validated": line.validated,
    }

    # Agregar información de tarea si existe
    if line.task:
        result["task_id"] = line.task.id
        result["task_name"] = line.task.name

    return result


@tool
def create_timesheet_entries(
    runtime: ToolRuntime[Context], entries_json: str
) -> str:
    """Create one or multiple timesheet entries for the current employee.
    
    This is a unified tool that handles both single and batch timesheet creation.
    You can create from 1 to N entries in a single call.

    Args:
        runtime: Runtime context containing employee_id
        entries_json: JSON string with array of entries (minimum 1). Each entry should have:
                     - project_id (int): ID of the project
                     - task_id (int | null): ID of the task (optional, use null if no task)
                     - hours (float): Number of hours
                     - date_str (str): Date in YYYY-MM-DD or "hoy"/"today"
                     - description (str, optional): Leave empty unless user explicitly requests one. Default: empty.

    Example entries_json for single entry (no description):
        '[{"project_id": 101, "task_id": 523, "hours": 8.0, "date_str": "2024-11-14"}]'
    
    Example entries_json with user-requested description:
        '[{"project_id": 101, "task_id": 523, "hours": 8.0, "date_str": "2024-11-14", "description": "Revisión de código"}]'

    Returns:
        JSON string with the created timesheet entries details
    """
    try:
        # Obtener employee_id del contexto
        employee_id = runtime.context.employee_id

        # Parsear el JSON de entrada
        try:
            entries_data = json.loads(entries_json)
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": "JSON inválido",
                    "message": f"Error al parsear JSON: {str(e)}",
                },
                ensure_ascii=False,
            )

        if not isinstance(entries_data, list):
            return json.dumps(
                {
                    "success": False,
                    "error": "Formato inválido",
                    "message": "El JSON debe ser un array de entradas",
                },
                ensure_ascii=False,
            )

        # Obtener la conexión a Odoo
        odoo_connection = get_odoo_connection()
        timesheet_gateway = OdooTimesheetLineGateway(odoo_connection)

        # Validar que hay al menos 1 entrada
        if len(entries_data) == 0:
            return json.dumps(
                {
                    "success": False,
                    "error": "Sin entradas",
                    "message": "Debes proporcionar al menos una entrada de timesheet",
                },
                ensure_ascii=False,
            )

        # Crear todas las requests
        requests = []
        for idx, entry in enumerate(entries_data):
            try:
                # Validar campos requeridos (task_id es opcional, puede ser null)
                if not all(
                    k in entry for k in ["project_id", "hours", "date_str"]
                ):
                    return json.dumps(
                        {
                            "success": False,
                            "error": "Campos faltantes",
                            "message": f"Entrada {idx + 1}: Faltan campos requeridos (project_id, hours, date_str)",
                        },
                        ensure_ascii=False,
                    )

                # Parsear fecha
                entry_date = _parse_date(entry["date_str"])

                # task_id puede ser null/None (opcional)
                task_id = entry.get("task_id")
                if task_id == "null" or task_id == "None":
                    task_id = None

                # Crear request
                request = CargarHorasRequest(
                    name=entry.get("description") if entry.get("description") else None,
                    employee_id=employee_id,
                    project_id=entry["project_id"],
                    hours=entry["hours"],
                    date=entry_date,
                    task_id=task_id,
                )
                requests.append(request)

            except ValueError as e:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Error en entrada",
                        "message": f"Entrada {idx + 1}: {str(e)}",
                    },
                    ensure_ascii=False,
                )

        # Ejecutar el use case con todas las requests
        use_case = CargarHorasUseCase(timesheet_gateway)
        created_lines = use_case.execute(requests)

        if not created_lines:
            return json.dumps(
                {
                    "success": False,
                    "error": "Error al crear",
                    "message": "No se pudieron crear las entradas de timesheet",
                },
                ensure_ascii=False,
            )

        # Retornar información de todas las entradas creadas
        return json.dumps(
            {
                "success": True,
                "message": f"{len(created_lines)} entrada(s) de timesheet creada(s) exitosamente",
                "total_created": len(created_lines),
                "timesheets": [_timesheet_line_to_dict(line) for line in created_lines],
            },
            ensure_ascii=False,
        )

    except InvalidHoursError as e:
        return json.dumps(
            {"success": False, "error": "Horas inválidas", "message": str(e)},
            ensure_ascii=False,
        )

    except TimesheetCreationError as e:
        return json.dumps(
            {"success": False, "error": "Error al crear timesheets", "message": str(e)},
            ensure_ascii=False,
        )

    except TimesheetNotFoundError as e:
        return json.dumps(
            {"success": False, "error": "Timesheets no encontrados", "message": str(e)},
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": "Error inesperado",
                "message": f"Ocurrió un error al crear las entradas: {str(e)}",
            },
            ensure_ascii=False,
        )


@tool
def get_timesheet_entries_by_date_range(
    runtime: ToolRuntime[Context], date_from_str: str, date_to_str: str
) -> str:
    """Get all timesheet entries for the current employee within a date range.

    This tool is useful to retrieve historical timesheet entries so the agent can replicate
    the same time entries from a previous period (e.g., "load hours like last week").

    Args:
        runtime: Runtime context containing employee_id
        date_from_str: Start date in format YYYY-MM-DD (e.g., "2024-11-01") or "hoy"/"today"
        date_to_str: End date in format YYYY-MM-DD (e.g., "2024-11-07") or "hoy"/"today"

    Returns:
        JSON string with the timesheet entries found in the date range, including:
        - project_id, project_name
        - task_id, task_name (if applicable)
        - hours
        - date
        - description

        This information can be used to create similar entries for a new date range.
    """
    try:
        # Obtener employee_id del contexto
        employee_id = runtime.context.employee_id

        # Parsear las fechas
        try:
            date_from = _parse_date(date_from_str)
        except ValueError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": "Fecha de inicio inválida",
                    "message": str(e),
                },
                ensure_ascii=False,
            )

        try:
            date_to = _parse_date(date_to_str)
        except ValueError as e:
            return json.dumps(
                {"success": False, "error": "Fecha de fin inválida", "message": str(e)},
                ensure_ascii=False,
            )

        # Validar que date_from no sea mayor que date_to
        if date_from > date_to:
            return json.dumps(
                {
                    "success": False,
                    "error": "Rango de fechas inválido",
                    "message": f"La fecha de inicio ({date_from}) no puede ser mayor que la fecha de fin ({date_to})",
                },
                ensure_ascii=False,
            )

        # Obtener la conexión a Odoo
        odoo_connection = get_odoo_connection()

        # Crear el gateway de timesheet
        timesheet_gateway = OdooTimesheetLineGateway(odoo_connection)

        # Obtener las líneas de timesheet del empleado en el rango de fechas
        timesheet_lines = timesheet_gateway.all(
            employee_id=employee_id, date_from=date_from, date_to=date_to
        )

        if not timesheet_lines:
            return json.dumps(
                {
                    "success": True,
                    "message": f"No se encontraron entradas de timesheet entre {date_from} y {date_to}",
                    "employee_id": employee_id,
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                    "total_entries": 0,
                    "total_hours": 0,
                    "entries": [],
                },
                ensure_ascii=False,
            )

        # Convertir las líneas a formato JSON-serializable
        entries = []
        total_hours = 0

        for line in timesheet_lines:
            entry = {
                "id": line.id,
                "project_id": line.project.id,
                "project_name": line.project.name,
                "hours": line.hours,
                "date": line.date.isoformat(),
                "description": line.name if line.name else "",
                "validated": line.validated,
            }

            # Agregar información de tarea si existe
            if line.task:
                entry["task_id"] = line.task.id
                entry["task_name"] = line.task.name
            else:
                entry["task_id"] = None
                entry["task_name"] = None

            entries.append(entry)
            total_hours += line.hours

        # Ordenar por fecha
        entries.sort(key=lambda x: x["date"])

        # Agrupar por día para dar un resumen más útil
        hours_by_date = {}
        for entry in entries:
            date_key = entry["date"]
            if date_key not in hours_by_date:
                hours_by_date[date_key] = 0
            hours_by_date[date_key] += entry["hours"]

        return json.dumps(
            {
                "success": True,
                "message": f"Se encontraron {len(entries)} entrada(s) de timesheet",
                "employee_id": employee_id,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "total_entries": len(entries),
                "total_hours": round(total_hours, 2),
                "hours_by_date": hours_by_date,
                "entries": entries,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": "Error inesperado",
                "message": f"Ocurrió un error al obtener las entradas de timesheet: {str(e)}",
            },
            ensure_ascii=False,
        )
