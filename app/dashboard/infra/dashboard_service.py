from datetime import date
from typing import List, Dict, Any, cast, Optional
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
)


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
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene datos de timesheet del equipo haciendo consulta directa a Odoo.
        """
        try:
            # Construir dominio para filtrar por equipo
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
        days_in_period = (date_to - date_from).days + 1

        total_daily_average = (
            total_hours / days_in_period if days_in_period > 0 else 0.0
        )
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

        except Exception as e:
            # En caso de error, retornar nombres genéricos
            return {emp_id: f"Empleado {emp_id}" for emp_id in employee_ids}

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
            except:
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
