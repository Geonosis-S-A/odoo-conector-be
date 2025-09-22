from typing import List
from app.personal_time.domain.gateway import LeaveTypeGateway
from app.personal_time.domain.models import LeaveType


class GetLeaveTypesUseCase:
    """Caso de uso para obtener todos los tipos de licencias disponibles."""
    
    def __init__(self, leave_type_gateway: LeaveTypeGateway):
        """Inicializa el caso de uso con el gateway de tipos de licencias.
        
        Args:
            leave_type_gateway: Gateway para acceder a los tipos de licencias
        """
        self.leave_type_gateway = leave_type_gateway
    
    def execute(self) -> List[LeaveType]:
        """Ejecuta el caso de uso para obtener todos los tipos de licencias.
        
        Returns:
            List[LeaveType]: Lista de tipos de licencias disponibles
            
        Raises:
            Exception: Si hay un error al obtener los tipos de licencias
        """
        try:
            leave_types = self.leave_type_gateway.get_all_leave_types()
            return leave_types
        except Exception as e:
            raise Exception(f"Error en el caso de uso GetLeaveTypes: {str(e)}")
