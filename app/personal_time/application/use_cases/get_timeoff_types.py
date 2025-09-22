from typing import List
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.domain.models import TimeOffType


class GetTimeOffTypesUseCase:
    """Caso de uso para obtener todos los tipos de licencias disponibles."""
    
    def __init__(self, timeoff_gateway: TimeOffGateway):
        """Inicializa el caso de uso con el gateway de tipos de licencias.
        
        Args:
            timeoff_gateway: Gateway para acceder a los tipos de licencias
        """
        self.timeoff_gateway = timeoff_gateway
    
    def execute(self) -> List[TimeOffType]:
        """Ejecuta el caso de uso para obtener todos los tipos de licencias.
        
        Returns:
            List[TimeOffType]: Lista de tipos de licencias disponibles
            
        Raises:
            Exception: Si hay un error al obtener los tipos de licencias
        """
        try:
            timeoff_types = self.timeoff_gateway.get_all_timeoff_types()
            return timeoff_types
        except Exception as e:
            raise Exception(f"Error en el caso de uso GetTimeOffTypes: {str(e)}")
