from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Any

from app.dashboard.domain.models import KPI
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.task.domain.gateway import TaskGateway
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.dashboard.domain.models import ProjectTotal, TaskTotal, EmployeeTotal


class DashboardDataService(ABC):
    """Gateway abstracto para obtener datos necesarios para el dashboard."""

    @abstractmethod
    def get_timesheet_summary(
        self,
        members_ids: list[int],
        date_from: date,
        date_to: date,
        task_gateway: TaskGateway,
        timesheet_line_gateway: TimesheetLineGateway,
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene datos de timesheet del equipo para el período especificado.

        Args:
            user_id: ID del usuario que solicita el dashboard (para filtro de equipo)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            task_gateway: Gateway de tareas para obtener información de parent_id
            timesheet_line_gateway: Gateway de líneas de timesheet para obtener datos del equipo
        Returns:
            Lista de DetailedTimesheetLine del equipo en el período
        """
        pass
    
    @abstractmethod
    def calculate_hours_kpi(self, timesheet_data: List[DetailedTimesheetLine], users_count: int) -> KPI:
        """Calcula el KPI de horas del período seleccionado."""
        pass
    
    @abstractmethod
    def calculate_entries_kpi(self, timesheet_data: List[DetailedTimesheetLine], users_count: int) -> KPI:
        """Calcula el KPI de entradas del período seleccionado."""
        pass
    
    @abstractmethod
    def calculate_daily_average_kpi(self, timesheet_data: List[DetailedTimesheetLine], users_count: int, date_from: date, date_to: date) -> KPI:
        """Calcula el KPI de promedio diario de horas."""
        pass
    
    @abstractmethod
    def calculate_project_totals(self, timesheet_data: List[DetailedTimesheetLine]) -> List[ProjectTotal]:
        """Calcula los totales de horas por proyecto."""
        pass
    
    @abstractmethod
    def calculate_task_totals(self, timesheet_data: List[DetailedTimesheetLine]) -> List[TaskTotal]:
        """Calcula los totales de horas por tarea."""
        pass
    
    @abstractmethod
    def calculate_employee_totals(self, timesheet_data: List[DetailedTimesheetLine], team_users: List[dict]) -> List[EmployeeTotal]:
        """Calcula los totales de horas por empleado."""
        pass