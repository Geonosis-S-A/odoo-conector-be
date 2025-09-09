from abc import ABC, abstractmethod
from datetime import date
from typing import List

from app.timesheet_line.domain.models import DetailedTimesheetLine


class DashboardDataGateway(ABC):
    """Gateway abstracto para obtener datos necesarios para el dashboard."""

    @abstractmethod
    def get_team_timesheet_data(
        self, 
        user_id: int, 
        date_from: date, 
        date_to: date
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene datos de timesheet del equipo para el período especificado.
        
        Args:
            user_id: ID del usuario que solicita el dashboard (para filtro de equipo)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            
        Returns:
            Lista de DetailedTimesheetLine del equipo en el período
        """
        pass
    
    @abstractmethod
    def get_active_team_users_count(self, user_id: int) -> int:
        """
        Obtiene la cantidad de usuarios activos en el equipo.
        
        Args:
            user_id: ID del usuario que solicita el dashboard (para filtro de equipo)
            
        Returns:
            Número de usuarios activos en el equipo
        """
        pass
