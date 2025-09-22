from abc import ABC, abstractmethod
from typing import List
from app.personal_time.domain.models import LeaveType


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
