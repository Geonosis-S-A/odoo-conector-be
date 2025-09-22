from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from app.personal_time.domain.models import TimeOffType, TimeOffRequest, TimeOffRequestResult, TimeOffRequestInfo


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

    @abstractmethod
    def get_employee_timeoff_requests(
        self, 
        employee_id: int, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> List[TimeOffRequestInfo]:
        """Obtiene las solicitudes de tiempo personal de un empleado, opcionalmente filtradas por fechas.
        
        Args:
            employee_id: ID del empleado en Odoo
            date_from: Fecha de inicio del filtro (opcional). Si se especifica, solo retorna
                      solicitudes cuya fecha de inicio sea mayor o igual a esta fecha.
            date_to: Fecha de fin del filtro (opcional). Si se especifica, solo retorna
                    solicitudes cuya fecha de fin sea menor o igual a esta fecha.
            
        Returns:
            List[TimeOffRequestInfo]: Lista de solicitudes del empleado filtradas por fecha
            
        Raises:
            Exception: Si hay un error al obtener las solicitudes
            ValueError: Si date_from > date_to
        """
        pass
