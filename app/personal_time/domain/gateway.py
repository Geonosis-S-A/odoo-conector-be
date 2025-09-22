from abc import ABC, abstractmethod
from typing import List
from app.personal_time.domain.models import LeaveType, LeaveRequest, LeaveRequestResult


class LeaveTypeGateway(ABC):
    """Gateway abstracto para operaciones con tipos de licencias."""
    
    @abstractmethod
    def get_all_leave_types(self) -> List[LeaveType]:
        """Obtiene todos los tipos de licencias disponibles.
        
        Returns:
            List[LeaveType]: Lista de tipos de licencias disponibles
            
        Raises:
            Exception: Si hay un error al obtener los tipos de licencias
        """
        pass

    @abstractmethod
    def create_leave_request(self, leave_request: LeaveRequest) -> LeaveRequestResult:
        """Crea una nueva solicitud de licencia en Odoo.
        
        Args:
            leave_request: Solicitud de licencia a crear
            
        Returns:
            LeaveRequestResult: Resultado de la operación con ID si es exitosa
            
        Raises:
            Exception: Si hay un error al crear la solicitud
        """
        pass
