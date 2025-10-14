from datetime import date
from typing import List, Dict, Any, Optional
from app.dashboard.domain.repositories import DashboardDataService
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.task.domain.models import TaskInfo, TaskWithParentInfo
from app.shared.infra.external.odoo.odoo_client import OdooConnection
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.task.domain.gateway import TaskGateway
from app.users.domain.repositories import EmployeeGateway
from app.dashboard.domain.models import (
    KPI,
    ProjectTotal,
    TaskTotal,
    EmployeeTotal,
    HierarchicalSummary,
    HierarchicalItem,
)
import uuid


class OdooDashboardDataService(DashboardDataService):
    """Implementación concreta del gateway de datos para dashboard usando Odoo directamente."""

    def __init__(
        self,
        odoo_client: OdooConnection,
        employee_gateway: EmployeeGateway,
        task_gateway: TaskGateway,
        timesheet_line_gateway: TimesheetLineGateway,
    ):
        self.odoo_client = odoo_client
        self.employee_gateway = employee_gateway
        self.task_gateway = task_gateway
        self.timesheet_line_gateway = timesheet_line_gateway

    def get_timesheet_summary(
        self,
        members_ids: list[int],
        date_from: date,
        date_to: date,
        task_gateway: TaskGateway,
        timesheet_line_gateway: TimesheetLineGateway,
        requester_user_id: int | None = None,
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene datos de timesheet del equipo haciendo consulta directa a Odoo.
        """
        try:
            # Construir dominio para filtrar por equipo
            if requester_user_id is not None:
                odoo_timesheet_lines = (
                    timesheet_line_gateway.all_by_employees_with_requester_user_id(
                        members_ids, date_from, date_to, requester_user_id
                    )
                )
            else:
                odoo_timesheet_lines = timesheet_line_gateway.all_by_employees(
                    members_ids, date_from, date_to
                )

            # Obtener información completa de las tareas para manejar parent_id
            task_ids = []
            for line in odoo_timesheet_lines:
                task_id_info = line.get("task_id")
                if (
                    task_id_info
                    and isinstance(task_id_info, list)
                    and len(task_id_info) > 0
                ):
                    task_ids.append(task_id_info[0])

            task_info_map = (
                task_gateway.get_tasks_info_with_parents(task_ids) if task_ids else {}
            )

            # Transformar datos de Odoo a nuestro modelo de dominio
            parsed_lines = [
                self._transform_odoo_to_detailed_domain(line, task_info_map)
                for line in odoo_timesheet_lines
            ]

            return parsed_lines

        except Exception as e:
            raise Exception(f"Error al obtener datos de timesheet del equipo: {str(e)}")

    def calculate_hours_kpi(
        self, timesheet_data: List[DetailedTimesheetLine], users_count: int
    ) -> KPI:
        """Calcula el KPI de horas del período seleccionado."""
        total_hours = sum(record.hours for record in timesheet_data)
        average_per_user = total_hours / users_count if users_count > 0 else 0.0

        return KPI(total=total_hours, average_per_user=average_per_user)

    def calculate_entries_kpi(
        self, timesheet_data: List[DetailedTimesheetLine], users_count: int
    ) -> KPI:
        """Calcula el KPI de entradas del período seleccionado."""
        total_entries = len(timesheet_data)
        average_per_user = total_entries / users_count if users_count > 0 else 0.0

        return KPI(total=float(total_entries), average_per_user=average_per_user)

    def calculate_daily_average_kpi(
        self,
        timesheet_data: List[DetailedTimesheetLine],
        users_count: int,
        date_from: date,
        date_to: date,
    ) -> KPI:
        """Calcula el KPI de promedio diario de horas."""
        total_hours = sum(record.hours for record in timesheet_data)
        worked_days = len(set(record.date for record in timesheet_data))

        total_daily_average = total_hours / worked_days if worked_days > 0 else 0.0
        average_per_user = total_daily_average / users_count if users_count > 0 else 0.0

        return KPI(
            total=total_daily_average,
            average_per_user=average_per_user,
            unit="hours/day",
        )

    def calculate_project_totals(
        self, timesheet_data: List[DetailedTimesheetLine]
    ) -> List[ProjectTotal]:
        """Calcula totales de horas por proyecto."""
        project_totals = {}

        for record in timesheet_data:
            project_id = record.project.id
            if project_id not in project_totals:
                project_totals[project_id] = {"name": record.project.name, "hours": 0.0}
            project_totals[project_id]["hours"] += record.hours

        # Convertir a lista de ProjectTotal ordenada por horas (mayor a menor)
        project_list = [
            ProjectTotal(
                project_id=project_id, project_name=data["name"], hours=data["hours"]
            )
            for project_id, data in project_totals.items()
        ]

        project_list.sort(key=lambda x: x.hours, reverse=True)

        return project_list

    def calculate_task_totals(
        self, timesheet_data: List[DetailedTimesheetLine]
    ) -> List[TaskTotal]:
        """Calcula totales de horas por tarea (solo tareas principales, ignora subtareas)."""
        task_totals = {}

        for record in timesheet_data:
            # Solo procesar si tiene tarea
            if record.task:
                task_id = record.task.id
                # Aquí podríamos filtrar subtareas si fuera necesario
                # Por ahora incluimos todas las tareas
                if task_id not in task_totals:
                    task_totals[task_id] = {
                        "name": record.task.name,
                        "hours": 0.0,
                        "project_id": record.task.project_id,
                    }
                task_totals[task_id]["hours"] += record.hours

        # Convertir a lista de TaskTotal ordenada por horas (mayor a menor)
        task_list = [
            TaskTotal(
                task_id=task_id,
                task_name=data["name"],
                hours=data["hours"],
                project_id=data["project_id"],
            )
            for task_id, data in task_totals.items()
        ]

        task_list.sort(key=lambda x: x.hours, reverse=True)

        return task_list

    def calculate_employee_totals(
        self, timesheet_data: List[DetailedTimesheetLine], team_users: List[dict]
    ) -> List[EmployeeTotal]:
        """Calcula totales de horas por empleado con nombres obtenidos de Odoo.

        Incluye todos los empleados del equipo, mostrando 0 horas para aquellos
        que no registraron tiempo en el período seleccionado.
        """
        # Inicializar todos los empleados del equipo con 0 horas
        employee_totals = {}
        for user in team_users:
            employee_id = user["id"]
            employee_totals[employee_id] = 0.0

        # Agrupar horas por empleado (solo para los que tienen registros)
        for record in timesheet_data:
            employee_id = record.employee_id
            if employee_id in employee_totals:
                employee_totals[employee_id] += record.hours

        # Obtener nombres de empleados desde Odoo
        employee_names = self.get_employee_names(list(employee_totals.keys()))

        # Crear lista de EmployeeTotal
        employee_list = [
            EmployeeTotal(
                user_id=employee_id,
                employee_name=employee_names.get(
                    employee_id, f"Empleado {employee_id}"
                ),
                hours=hours,
            )
            for employee_id, hours in employee_totals.items()
        ]

        employee_list.sort(key=lambda x: x.hours, reverse=True)

        return employee_list

    def get_employee_names(self, employee_ids: List[int]) -> dict:
        """Obtiene los nombres de los empleados desde Odoo usando el EmployeeGateway."""
        try:
            employee_names = {}

            # Si no hay empleados, retornar diccionario vacío
            if not employee_ids:
                return employee_names

            # Obtener información de cada empleado usando el gateway
            for employee_id in employee_ids:
                employee = self.employee_gateway.get_by_id(employee_id)
                if employee:
                    employee_names[employee_id] = employee.full_name
                else:
                    # Si no se encuentra el empleado, usar nombre genérico
                    employee_names[employee_id] = f"Empleado {employee_id}"

            return employee_names

        except Exception:
            # En caso de error, retornar nombres genéricos
            return {emp_id: f"Empleado {emp_id}" for emp_id in employee_ids}

    def calculate_project_without_task_totals(
        self, project_totals: List[ProjectTotal], task_totals: List[TaskTotal]
    ) -> List[TaskTotal]:
        """
        Calcula las horas cargadas directamente a proyectos sin tarea específica.

        Compara los totales por proyecto con los totales por tarea para determinar
        qué horas fueron cargadas directamente al proyecto sin asignar a una tarea.

        Args:
            project_totals: Lista de totales por proyecto
            task_totals: Lista de totales por tarea

        Returns:
            Lista de ProjectWithoutTaskTotal con las horas cargadas sin tarea
        """
        # Crear un diccionario para sumar las horas por proyecto desde las tareas
        task_hours_by_project = {}

        for task in task_totals:
            project_id = task.project_id
            if project_id not in task_hours_by_project:
                task_hours_by_project[project_id] = 0.0
            task_hours_by_project[project_id] += task.hours

        # Calcular las horas sin tarea para cada proyecto
        project_without_task_list = []

        for project in project_totals:
            project_id = project.project_id
            total_project_hours = project.hours
            task_hours = task_hours_by_project.get(project_id, 0.0)

            # Las horas sin tarea son la diferencia entre el total del proyecto y las horas de tareas
            hours_without_task = total_project_hours - task_hours

            # Solo incluir proyectos que tienen horas cargadas sin tarea
            if hours_without_task > 0:
                project_without_task_list.append(
                    TaskTotal(
                        task_id=int(uuid.uuid4()),
                        project_id=project_id,
                        task_name="Sin tarea",
                        hours=hours_without_task,
                    )
                )

        # Ordenar por horas sin tarea (mayor a menor)
        project_without_task_list.sort(key=lambda x: x.hours, reverse=True)

        return project_without_task_list

    def _transform_odoo_to_detailed_domain(
        self,
        odoo_line: Dict[str, Any],
        task_info_map: Optional[Dict[int, TaskWithParentInfo]] = None,
    ) -> DetailedTimesheetLine:
        """
        Transforma una línea de Odoo al modelo de dominio DetailedTimesheetLine.
        """
        from datetime import datetime

        # Extraer información del proyecto
        project_info = odoo_line.get("project_id")
        if project_info and isinstance(project_info, list) and len(project_info) >= 2:
            project = Project(id=project_info[0], name=project_info[1])
        else:
            # Proyecto por defecto si no hay información
            project = Project(id=0, name="Sin proyecto")

        # Extraer información de la tarea
        task_info = odoo_line.get("task_id")
        task = None
        if task_info and isinstance(task_info, list) and len(task_info) >= 2:
            task_id = task_info[0]
            task_name = task_info[1]

            # Si tenemos información completa de la tarea, usar nombre con concatenación si aplica
            if task_info_map and task_id in task_info_map:
                task_with_parent = task_info_map[task_id]
                task_name = task_with_parent.get_display_name()

            task = TaskInfo(
                id=task_id,
                name=task_name,
                project_id=project.id,
                project_name=project.name,
            )

        # Extraer información del empleado
        employee_info = odoo_line.get("employee_id")
        employee_id = (
            employee_info[0] if employee_info and isinstance(employee_info, list) else 0
        )

        # Parsear fecha de creación
        create_date = None
        if odoo_line.get("create_date"):
            try:
                create_date = datetime.fromisoformat(
                    odoo_line["create_date"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                create_date = None

        # Parsear fecha
        line_date = datetime.strptime(odoo_line["date"], "%Y-%m-%d").date()

        return DetailedTimesheetLine(
            id=odoo_line["id"],
            name=odoo_line.get("name", ""),
            employee_id=employee_id,
            project=project,
            task=task,
            hours=float(odoo_line.get("unit_amount", 0)),
            date=line_date,
            validated=bool(odoo_line.get("validated", False)),
            create_date=create_date,
            notification=None,  # No necesitamos notificaciones para dashboard
        )

    def _get_task_display_name_for_hierarchy(self, task_with_parent_info) -> str:
        """
        Obtiene el nombre de la tarea SIN concatenación para la estructura jerárquica.
        A diferencia de get_display_name(), esto retorna solo el nombre de la tarea.
        """
        return task_with_parent_info.name

    def _clean_task_name_for_hierarchy(self, task_name: str) -> str:
        """
        Limpia el nombre de una tarea que puede estar concatenado con flecha.
        Retorna solo la parte después de la flecha (→) si existe, o el nombre completo si no.

        Ejemplos:
        - "Tarea Padre → Subtarea" -> "Subtarea"
        - "Tarea Simple" -> "Tarea Simple"
        """
        if " → " in task_name:
            return task_name.split(" → ")[-1].strip()
        return task_name

    def calculate_hierarchical_summary(
        self,
        timesheet_data: List[DetailedTimesheetLine],
        task_gateway: TaskGateway,
        timesheet_costs: Optional[Dict[int, float]] = None,
    ) -> HierarchicalSummary:
        """
        Calcula la estructura jerárquica de proyectos y tareas con casos borde.

        Esta implementación maneja:
        1. Horas cargadas directamente a proyectos sin tarea → Tarea artificial "Sin tarea"
        2. Horas cargadas a tareas padre sin subtareas → Subtarea artificial "Sin subtarea"
        3. Estructura anidada Proyecto → Tarea → Subtarea
        4. Acumulación de costos si están disponibles
        """
        # Diccionario para agrupar por proyecto
        projects_data = {}

        # Ya no necesitamos contadores para IDs artificiales
        # Los elementos artificiales usan el ID del padre

        # Crear diccionario de costos si no está disponible
        if timesheet_costs is None:
            timesheet_costs = {}

        # Agrupar datos por proyecto
        for line in timesheet_data:
            project_id = line.project.id
            project_name = line.project.name

            if project_id not in projects_data:
                projects_data[project_id] = {
                    "name": project_name,
                    "total_hours": 0.0,
                    "total_cost": 0.0,
                    "tasks": {},
                    "direct_hours": 0.0,  # Horas cargadas directamente al proyecto
                    "direct_cost": 0.0,  # Costo cargado directamente al proyecto
                }

            projects_data[project_id]["total_hours"] += line.hours
            line_cost = timesheet_costs.get(line.id, 0.0) or 0.0
            projects_data[project_id]["total_cost"] += line_cost

            if line.task:
                task_id = line.task.id
                task_name = self._clean_task_name_for_hierarchy(line.task.name)

                if task_id not in projects_data[project_id]["tasks"]:
                    projects_data[project_id]["tasks"][task_id] = {
                        "name": task_name,
                        "total_hours": 0.0,
                        "total_cost": 0.0,
                        "subtasks": {},
                        "direct_hours": 0.0,  # Horas cargadas directamente a la tarea
                        "direct_cost": 0.0,  # Costo cargado directamente a la tarea
                        "parent_id": None,
                        "is_virtual_parent": False,  # Campo auxiliar: True si es padre invisible
                        "has_direct_hours": False,  # Campo auxiliar: True si tiene horas registradas directamente
                    }

                projects_data[project_id]["tasks"][task_id]["total_hours"] += line.hours
                projects_data[project_id]["tasks"][task_id]["total_cost"] += line_cost
                projects_data[project_id]["tasks"][task_id]["direct_hours"] += (
                    line.hours
                )
                projects_data[project_id]["tasks"][task_id]["direct_cost"] += line_cost
                projects_data[project_id]["tasks"][task_id]["has_direct_hours"] = True
            else:
                # Horas cargadas directamente al proyecto sin tarea
                projects_data[project_id]["direct_hours"] += line.hours
                projects_data[project_id]["direct_cost"] += line_cost

        # Obtener información de parent_id para todas las tareas
        all_task_ids = []
        for project_data in projects_data.values():
            all_task_ids.extend(project_data["tasks"].keys())

        # Primera consulta para obtener parent_ids
        initial_task_info_map = (
            task_gateway.get_tasks_info_with_parents(all_task_ids)
            if all_task_ids
            else {}
        )

        # Identificar parent_ids que no están en all_task_ids
        additional_parent_ids = set()
        for task_info in initial_task_info_map.values():
            if task_info.parent_id and task_info.parent_id not in all_task_ids:
                additional_parent_ids.add(task_info.parent_id)

        # Segunda consulta para obtener información de los padres faltantes
        parent_task_info_map = {}
        if additional_parent_ids:
            parent_task_info_map = task_gateway.get_tasks_info_with_parents(
                list(additional_parent_ids)
            )

        # Combinar ambos mapas
        task_info_map = {**initial_task_info_map, **parent_task_info_map}

        # Organizar tareas por parent_id y calcular horas directas vs subtareas
        for project_id, project_data in projects_data.items():
            # Identificar tareas padre e hijas
            parent_tasks = {}
            orphaned_subtasks = {}  # Subtareas cuyo padre no está registrado

            for task_id, task_data in project_data["tasks"].items():
                if task_id in task_info_map:
                    parent_id = task_info_map[task_id].parent_id
                    if parent_id:
                        # Es una subtarea
                        task_data["parent_id"] = parent_id
                        if parent_id in project_data["tasks"]:
                            # El padre existe, agregar como subtarea normal
                            if parent_id not in parent_tasks:
                                parent_tasks[parent_id] = {}
                            parent_tasks[parent_id][task_id] = task_data
                            # IMPORTANTE: Marcar para remover de tareas principales
                            # (se procesará después del loop)
                        else:
                            # El padre no existe, crear tarea padre virtual
                            if parent_id not in orphaned_subtasks:
                                orphaned_subtasks[parent_id] = []
                            orphaned_subtasks[parent_id].append((task_id, task_data))
                    else:
                        # Es tarea principal
                        if task_id not in parent_tasks:
                            parent_tasks[task_id] = {}

            # Remover subtareas de las tareas principales (ya están organizadas bajo sus padres)
            subtasks_to_remove = []
            for parent_id, subtasks in parent_tasks.items():
                for subtask_id in subtasks.keys():
                    if subtask_id in project_data["tasks"] and subtask_id != parent_id:
                        subtasks_to_remove.append(subtask_id)

            for subtask_id in subtasks_to_remove:
                del project_data["tasks"][subtask_id]

            # Crear tareas padre virtuales para subtareas huérfanas
            for parent_id, subtasks_list in orphaned_subtasks.items():
                if parent_id in task_info_map:
                    parent_info = task_info_map[parent_id]
                    # Crear tarea padre virtual
                    total_hours = sum(
                        subtask_data["total_hours"] for _, subtask_data in subtasks_list
                    )
                    total_cost = sum(
                        subtask_data.get("total_cost", 0.0)
                        for _, subtask_data in subtasks_list
                    )
                    parent_task_data = {
                        "name": self._get_task_display_name_for_hierarchy(parent_info),
                        "total_hours": total_hours,
                        "total_cost": total_cost,
                        "subtasks": {},
                        "direct_hours": 0.0,  # Las horas están todas en subtareas
                        "direct_cost": 0.0,  # Los costos están todos en subtareas
                        "parent_id": None,
                        "is_virtual_parent": True,  # PADRE INVISIBLE CREADO VIRTUALMENTE
                        "has_direct_hours": False,  # No tiene horas directas registradas
                    }

                    # Agregar subtareas al padre virtual
                    for subtask_id, subtask_data in subtasks_list:
                        parent_task_data["subtasks"][subtask_id] = subtask_data
                        # Remover la subtarea de las tareas principales
                        if subtask_id in project_data["tasks"]:
                            del project_data["tasks"][subtask_id]

                    # Agregar padre virtual a las tareas del proyecto
                    project_data["tasks"][parent_id] = parent_task_data
                    parent_tasks[parent_id] = parent_task_data["subtasks"]

            # Identificar tareas padre que existen en TaskGateway pero no en project_data
            # (caso: solo hay subtareas registradas, sin horas en la tarea padre)
            subtasks_needing_parent = {}
            for task_id, task_data in list(project_data["tasks"].items()):
                if task_data.get("parent_id"):
                    parent_id = task_data["parent_id"]
                    if (
                        parent_id not in project_data["tasks"]
                        and parent_id in task_info_map
                    ):
                        # La tarea padre existe en TaskGateway pero no tiene horas registradas
                        if parent_id not in subtasks_needing_parent:
                            subtasks_needing_parent[parent_id] = []
                        subtasks_needing_parent[parent_id].append((task_id, task_data))

            # Crear tareas padre para subtareas que necesitan padre
            for parent_id, subtasks_list in subtasks_needing_parent.items():
                parent_info = task_info_map[parent_id]
                total_hours = sum(
                    subtask_data["total_hours"] for _, subtask_data in subtasks_list
                )
                total_cost = sum(
                    subtask_data.get("total_cost", 0.0)
                    for _, subtask_data in subtasks_list
                )
                parent_task_data = {
                    "name": self._get_task_display_name_for_hierarchy(parent_info),
                    "total_hours": total_hours,
                    "total_cost": total_cost,
                    "subtasks": {},
                    "direct_hours": 0.0,  # Las horas están todas en subtareas
                    "direct_cost": 0.0,  # Los costos están todos en subtareas
                    "parent_id": None,
                    "is_virtual_parent": True,  # PADRE INVISIBLE CREADO VIRTUALMENTE
                    "has_direct_hours": False,  # No tiene horas directas registradas
                }

                # Agregar subtareas al padre
                for subtask_id, subtask_data in subtasks_list:
                    parent_task_data["subtasks"][subtask_id] = subtask_data
                    # Remover la subtarea de las tareas principales
                    if subtask_id in project_data["tasks"]:
                        del project_data["tasks"][subtask_id]

                # Agregar padre a las tareas del proyecto
                project_data["tasks"][parent_id] = parent_task_data
                parent_tasks[parent_id] = parent_task_data["subtasks"]

            # Calcular horas directas de tareas padre (excluyendo subtareas)
            for parent_task_id, subtasks in parent_tasks.items():
                if parent_task_id in project_data["tasks"]:
                    parent_task_data = project_data["tasks"][parent_task_id]
                    subtasks_hours = sum(
                        subtask["total_hours"] for subtask in subtasks.values()
                    )
                    subtasks_cost = sum(
                        subtask.get("total_cost", 0.0) for subtask in subtasks.values()
                    )

                    # Lógica simplificada con campos auxiliares
                    if parent_task_data.get("is_virtual_parent", False):
                        # PADRE VIRTUAL: Ya está configurado correctamente, no tocar
                        pass
                    else:
                        # PADRE REAL: Necesita recálculo de totales
                        if parent_task_data.get("has_direct_hours", False):
                            # Padre real CON horas directas: total = directas + subtareas
                            direct_hours = parent_task_data["direct_hours"]
                            direct_cost = parent_task_data.get("direct_cost", 0.0)
                            parent_task_data["total_hours"] = (
                                direct_hours + subtasks_hours
                            )
                            parent_task_data["total_cost"] = direct_cost + subtasks_cost
                        else:
                            # Padre real SIN horas directas: total = solo subtareas
                            parent_task_data["direct_hours"] = 0.0
                            parent_task_data["direct_cost"] = 0.0
                            parent_task_data["total_hours"] = subtasks_hours
                            parent_task_data["total_cost"] = subtasks_cost

                    # Almacenar subtareas en la tarea padre
                    parent_task_data["subtasks"] = subtasks

        # Construir estructura jerárquica
        hierarchical_items = []
        total_hours = 0.0
        total_cost = 0.0

        for project_id, project_data in projects_data.items():
            project_item = HierarchicalItem(
                type="project",
                id=project_id,
                name=project_data["name"],
                total_hours=project_data["total_hours"],
                total_cost=project_data.get("total_cost", 0.0),
                data=[],
                is_artificial=False,
            )

            # Agregar tareas principales al proyecto
            for task_id, task_data in project_data["tasks"].items():
                # Solo procesar tareas principales (sin parent_id)
                if not task_data.get("parent_id"):
                    task_item = self._build_task_item(task_id, task_data)
                    project_item.data.append(task_item)

            # Agregar tarea artificial "Sin tarea" si hay horas directas al proyecto
            if project_data["direct_hours"] > 0:
                sin_tarea_item = HierarchicalItem(
                    type="task",
                    id=project_id,  # Usar el ID del proyecto padre
                    name="Sin tarea",
                    total_hours=project_data["direct_hours"],
                    total_cost=project_data.get("direct_cost", 0.0),
                    data=[],
                    is_artificial=True,
                )
                project_item.data.append(sin_tarea_item)

            # Ordenar tareas por horas (mayor a menor)
            project_item.data.sort(key=lambda x: x.total_hours, reverse=True)

            # IMPORTANTE: Recalcular totales del proyecto basándose en las tareas finales
            # Los valores originales en project_data pueden estar desactualizados
            actual_project_hours = sum(task.total_hours for task in project_item.data)
            actual_project_cost = sum(
                task.total_cost or 0.0 for task in project_item.data
            )

            # Actualizar el proyecto con los totales correctos
            project_item.total_hours = actual_project_hours
            project_item.total_cost = (
                actual_project_cost if actual_project_cost > 0 else None
            )

            hierarchical_items.append(project_item)
            total_hours += actual_project_hours
            total_cost += actual_project_cost

        # Ordenar proyectos por horas (mayor a menor)
        hierarchical_items.sort(key=lambda x: x.total_hours, reverse=True)

        # OPTIMIZACIÓN: Eliminar nodos intermedios que solo tienen un hijo artificial
        optimized_items = []
        for project_item in hierarchical_items:
            optimized_project = self._optimize_single_artificial_children(project_item)
            optimized_items.append(optimized_project)

        return HierarchicalSummary(
            total_hours=total_hours,
            total_cost=total_cost if total_cost > 0 else None,
            data=optimized_items,
        )

    def _build_task_item(
        self,
        task_id: int,
        task_data: dict,
    ) -> HierarchicalItem:
        """
        Construye un elemento de tarea con sus subtareas.
        """
        task_item = HierarchicalItem(
            type="task",
            id=task_id,
            name=task_data["name"],
            total_hours=task_data["total_hours"],
            total_cost=task_data.get("total_cost", 0.0)
            if task_data.get("total_cost", 0.0) > 0
            else None,
            data=[],
            is_artificial=False,
        )

        # Agregar subtareas reales como nodos hoja directos
        for subtask_id, subtask_data in task_data["subtasks"].items():
            subtask_cost = subtask_data.get("total_cost", 0.0)
            subtask_item = HierarchicalItem(
                type="task",
                id=subtask_id,
                name=subtask_data["name"],
                total_hours=subtask_data["total_hours"],
                total_cost=subtask_cost if subtask_cost > 0 else None,
                data=[],  # Nodo hoja - sin hijos
                is_artificial=False,
            )
            task_item.data.append(subtask_item)

        # Agregar subtarea artificial "Sin subtarea" si hay horas directas a la tarea padre
        if task_data["direct_hours"] > 0:
            direct_cost = task_data.get("direct_cost", 0.0)
            sin_subtarea_padre_item = HierarchicalItem(
                type="task",
                id=task_id,  # Usar el ID de la tarea padre
                name="Sin subtarea",
                total_hours=task_data["direct_hours"],
                total_cost=direct_cost if direct_cost > 0 else None,
                data=[],
                is_artificial=True,
            )
            task_item.data.append(sin_subtarea_padre_item)

        # Ordenar subtareas por horas (mayor a menor)
        task_item.data.sort(key=lambda x: x.total_hours, reverse=True)

        return task_item

    def _optimize_single_artificial_children(
        self, item: HierarchicalItem
    ) -> HierarchicalItem:
        """
        Optimiza la estructura eliminando nodos intermedios que solo tienen un hijo artificial.

        Lógica:
        - Si un nodo tiene exactamente 1 hijo y ese hijo es artificial
        - Entonces el nodo se convierte en nodo hoja (sin hijos)
        - Esto elimina redundancia y reduce el tamaño del JSON

        Args:
            item: El nodo a optimizar

        Returns:
            El nodo optimizado
        """
        # Primero, optimizar recursivamente todos los hijos
        optimized_children = []
        for child in item.data:
            optimized_child = self._optimize_single_artificial_children(child)
            optimized_children.append(optimized_child)

        # Aplicar optimización al nodo actual
        if len(optimized_children) == 1 and optimized_children[0].is_artificial:
            # Caso de optimización: Un solo hijo artificial
            # Convertir este nodo en hoja (eliminar el hijo artificial redundante)
            return HierarchicalItem(
                type=item.type,
                id=item.id,
                name=item.name,
                total_hours=item.total_hours,
                total_cost=item.total_cost,
                data=[],  # Sin hijos, se convierte en nodo hoja
                is_artificial=False,  # El nodo real se mantiene como real
            )
        else:
            # No se aplica optimización, mantener estructura actual
            return HierarchicalItem(
                type=item.type,
                id=item.id,
                name=item.name,
                total_hours=item.total_hours,
                total_cost=item.total_cost,
                data=optimized_children,
                is_artificial=item.is_artificial,
            )

    def get_timesheet_by_task_or_project(
        self,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        timesheet_line_gateway: Optional[TimesheetLineGateway] = None,
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene líneas de timesheet filtradas por tarea o proyecto en un período específico.

        Args:
            task_id: ID de la tarea a filtrar (opcional)
            project_id: ID del proyecto a filtrar (opcional, usado cuando task_id es None)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            timesheet_line_gateway: Gateway de líneas de timesheet

        Returns:
            Lista de DetailedTimesheetLine que coinciden con los criterios
        """
        try:
            # Validar que el gateway esté presente
            if not timesheet_line_gateway:
                raise ValueError("timesheet_line_gateway es requerido")

            # Delegar la funcionalidad al TimesheetLineGateway
            return timesheet_line_gateway.get_by_task_or_project(
                task_id=task_id,
                project_id=project_id,
                date_from=date_from,
                date_to=date_to,
            )

        except Exception as e:
            raise Exception(f"Error al obtener timesheet por tarea/proyecto: {str(e)}")
