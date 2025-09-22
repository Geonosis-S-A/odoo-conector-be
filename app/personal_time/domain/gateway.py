from abc import ABC, abstractmethod
from typing import List
from app.personal_time.domain.models import TimeOffType, TimeOffRequest, TimeOffRequestResult


class TimeOffGateway(ABC):
    """Gateway abstracto para operaciones con tipos de licencias."""
    
    @abstractmethod
    def get_all_timeoff_types(self) -> List[TimeOffType]:
        """Obtiene todos los tipos de licencias disponibles.
        
        Returns:
            List[TimeOffType]: Lista de tipos de licencias disponibles
            
        Raises:
            Exception: Si hay un error al obtener los tipos de licencias
        """
        pass

    @abstractmethod
    def create_timeoff_request(self, timeoff_request: TimeOffRequest) -> TimeOffRequestResult:
        """Crea una nueva solicitud de licencia en Odoo.
        
        Args:
            timeoff_request: Solicitud de licencia a crear
            
        Returns:
            TimeOffRequestResult: Resultado de la operación con ID si es exitosa
            
        Raises:
            Exception: Si hay un error al crear la solicitud
        """
        pass
