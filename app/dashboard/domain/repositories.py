from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Any

from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.task.domain.gateway import TaskGateway
from app.timesheet_line.domain.repositories import TimesheetLineGateway


class DashboardDataService(ABC):
    """Gateway abstracto para obtener datos necesarios para el dashboard."""

    @abstractmethod
    def get_team_timesheet_data(
        self,
        user_id: int,
        employee_id: int,
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
