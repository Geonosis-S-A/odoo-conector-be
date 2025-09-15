from datetime import date
from typing import List, Optional

from app.dashboard.domain.repositories import DashboardDataService
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway


class GetTaskDetailUseCase:
    """Caso de uso para obtener el detalle de empleados que cargaron horas en una tarea o proyecto."""

    def __init__(
        self,
        dashboard_gateway: DashboardDataService,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
    ):
        self.dashboard_gateway = dashboard_gateway
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway

    def execute(
        self, 
        task_id: Optional[int], 
        project_id: Optional[int], 
        date_from: date, 
        date_to: date
    ) -> dict:
        """
        Ejecuta el caso de uso para obtener empleados que cargaron horas en una tarea/proyecto.

        Args:
            task_id: ID de la tarea (opcional)
            project_id: ID del proyecto (usado cuando task_id es None)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            dict con información detallada de las líneas de timesheet y estadísticas
        """
        
        # Validar parámetros de entrada
        if not task_id and not project_id:
            raise ValueError("Debe proporcionar task_id o project_id")
        
        if date_from > date_to:
            raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")

        # Obtener líneas de timesheet filtradas directamente desde el gateway
        timesheet_lines = self.timesheet_line_gateway.get_by_task_or_project(
            task_id=task_id,
            project_id=project_id,
            date_from=date_from,
            date_to=date_to,
        )

        # Obtener IDs únicos de empleados para buscar nombres
        unique_employee_ids = list(set(line.employee_id for line in timesheet_lines))
        
        # Obtener nombres de empleados
        employee_names = self._get_employee_names(unique_employee_ids)

        # Transformar a formato simplificado con información del empleado
        timesheet_lines_data = [
            self._transform_to_simple_format(line, employee_names) for line in timesheet_lines
        ]

        return {
            "task_id": task_id,
            "project_id": project_id,
            "timesheet_lines": timesheet_lines_data,
        }

    def _get_employee_names(self, employee_ids: List[int]) -> dict:
        """
        Obtiene los nombres de los empleados desde el EmployeeGateway.
        
        Args:
            employee_ids: Lista de IDs de empleados
            
        Returns:
            dict con mapping employee_id -> employee_name
        """
        employee_names = {}
        
        for employee_id in employee_ids:
            try:
                employee = self.employee_gateway.get_by_id(employee_id)
                if employee:
                    employee_names[employee_id] = employee.full_name
                else:
                    employee_names[employee_id] = f"Empleado {employee_id}"
            except Exception:
                employee_names[employee_id] = f"Empleado {employee_id}"
        
        return employee_names

    def _transform_to_simple_format(self, line: DetailedTimesheetLine, employee_names: dict) -> dict:
        """
        Transforma un DetailedTimesheetLine al formato simplificado solicitado.
        
        Args:
            line: Línea de timesheet del modelo de dominio
            employee_names: Mapping de employee_id -> employee_name
            
        Returns:
            dict compatible con SimpleTimesheetLineResponse
        """
        return {
            "id": line.id,
            "name": line.name,
            "employee": {
                "employee_id": line.employee_id,
                "employee_name": employee_names.get(line.employee_id, f"Empleado {line.employee_id}")
            },
            "hours": line.hours,
            "date": line.date,
             "create_date": line.create_date if line.create_date else None,
            "validated": line.validated,
            "notification": None,  # No incluimos notificaciones en dashboard
        }
