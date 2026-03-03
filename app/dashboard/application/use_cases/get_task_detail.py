from datetime import date
from typing import List, Optional

from app.dashboard.domain.repositories import DashboardDataService
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import (
    TimesheetLineGateway,
    TimesheetLineNotificationRepository,
)
from app.users.domain.repositories import EmployeeGateway


class GetTaskDetailUseCase:
    """Caso de uso para obtener el detalle de empleados que cargaron horas en una tarea o proyecto."""

    def __init__(
        self,
        dashboard_gateway: DashboardDataService,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
        notification_repository: TimesheetLineNotificationRepository,
    ):
        self.dashboard_gateway = dashboard_gateway
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway
        self.notification_repository = notification_repository

    def execute(
        self,
        task_id: Optional[int],
        project_id: Optional[int],
        date_from: date,
        date_to: date,
        employee_id: Optional[int] = None,
    ) -> dict:
        """
        Ejecuta el caso de uso para obtener empleados que cargaron horas en una tarea/proyecto.

        Args:
            task_id: ID de la tarea (opcional)
            project_id: ID del proyecto (usado cuando task_id es None)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            employee_id: ID del empleado para filtrar (opcional)

        Returns:
            dict con información detallada de las líneas de timesheet y estadísticas
        """

        # Validar parámetros de entrada
        if not task_id and not project_id:
            raise ValueError("Debe proporcionar task_id o project_id")

        if date_from > date_to:
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de fin"
            )

        # Obtener líneas de timesheet filtradas directamente desde el gateway
        timesheet_lines = self.timesheet_line_gateway.get_by_task_or_project(
            task_id=task_id,
            project_id=project_id,
            date_from=date_from,
            date_to=date_to,
        )

        # Filtrar por empleado específico si se proporciona employee_id
        if employee_id is not None:
            timesheet_lines = [
                line for line in timesheet_lines if line.employee_id == employee_id
            ]

        # Obtener IDs únicos de empleados para buscar nombres
        unique_employee_ids = list(set(line.employee_id for line in timesheet_lines))

        # Obtener nombres de empleados en una sola llamada batch
        employee_names = self._get_employee_names(unique_employee_ids)

        # Construir employees_dict solo con los empleados relevantes (batch)
        employees = self.employee_gateway.get_by_ids(unique_employee_ids)
        employees_dict = {employee.id: employee for employee in employees}

        # Obtener todas las notificaciones en una sola query batch
        timesheet_ids = [line.id for line in timesheet_lines]
        notifications_list = self.notification_repository.get_by_timesheet_ids(timesheet_ids)
        notifications_map = {n.timesheet_line_id: n for n in notifications_list}

        # Transformar a formato simplificado con información del empleado
        timesheet_lines_data = [
            self._transform_to_simple_format(line, employee_names, employees_dict, notifications_map)
            for line in timesheet_lines
        ]

        return {
            "task_id": task_id,
            "project_id": project_id,
            "timesheet_lines": timesheet_lines_data,
        }

    def _get_employee_names(self, employee_ids: List[int]) -> dict:
        """Obtiene los nombres de los empleados en una sola llamada batch."""
        if not employee_ids:
            return {}
        try:
            employees = self.employee_gateway.get_by_ids(employee_ids)
            employee_names = {emp.id: emp.full_name for emp in employees}
            for emp_id in employee_ids:
                employee_names.setdefault(emp_id, f"Empleado {emp_id}")
            return employee_names
        except Exception:
            return {emp_id: f"Empleado {emp_id}" for emp_id in employee_ids}

    def _transform_to_simple_format(
        self,
        line: DetailedTimesheetLine,
        employee_names: dict,
        employees_dict: dict,
        notifications_map: dict,
    ) -> dict:
        """
        Transforma un DetailedTimesheetLine al formato simplificado solicitado.

        Args:
            line: Línea de timesheet del modelo de dominio
            employee_names: Mapping de employee_id -> employee_name
            employees_dict: Mapping de employee_id -> employee object para notificaciones
            notifications_map: Mapping de timesheet_line_id -> TimesheetLineNotification
        """
        notification_data = None
        try:
            notification = notifications_map.get(line.id)
            if notification is not None:
                approver = employees_dict.get(notification.approver_id)
                notification_data = {
                    "id": notification.id,
                    "sender_name": approver.full_name if approver else f"Empleado {notification.approver_id}",
                    "sended_at": notification.created_at,
                }
        except Exception:
            pass

        return {
            "id": line.id,
            "name": line.name,
            "employee": {
                "employee_id": line.employee_id,
                "employee_name": employee_names.get(
                    line.employee_id, f"Empleado {line.employee_id}"
                ),
            },
            "hours": line.hours,
            "date": line.date,
            "create_date": line.create_date if line.create_date else None,
            "validated": line.validated,
            "notification": notification_data,
        }
