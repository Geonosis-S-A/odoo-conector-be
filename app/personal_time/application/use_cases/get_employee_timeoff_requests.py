from datetime import date
from typing import List, Optional
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.domain.models import TimeOffRequestInfo


class GetEmployeeTimeOffRequestsUseCase:
    """Caso de uso para obtener las solicitudes de tiempo personal de un empleado."""
    
    def __init__(self, timeoff_gateway: TimeOffGateway):
        """Inicializa el caso de uso con el gateway de tipos de licencias.
        
        Args:
            timeoff_gateway: Gateway para acceder a las operaciones de licencias
        """
        self.timeoff_gateway = timeoff_gateway
    
    def execute(
        self, 
        employee_id: int, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> List[TimeOffRequestInfo]:
        """Ejecuta el caso de uso para obtener las solicitudes de tiempo personal de un empleado.
        
        Args:
            employee_id: ID del empleado en Odoo
            date_from: Fecha de inicio del filtro (opcional). Si se especifica, solo retorna
                      solicitudes cuya fecha de inicio sea mayor o igual a esta fecha.
            date_to: Fecha de fin del filtro (opcional). Si se especifica, solo retorna
                    solicitudes cuya fecha de fin sea menor o igual a esta fecha.
            
        Returns:
            List[TimeOffRequestInfo]: Lista de solicitudes del empleado filtradas por fecha
            
        Raises:
            Exception: Si hay un error al obtener las solicitudes o validar parámetros
        """

        if date_from and date_to and date_from > date_to:
            raise ValueError("Error: fechas inválidas")
        


        try:
            # Delegar al gateway para obtener las solicitudes
            timeoff_requests = self.timeoff_gateway.get_employee_timeoff_requests(
                employee_id=employee_id,
                date_from=date_from,
                date_to=date_to
            )
            
            return timeoff_requests
            
        except Exception as e:
            raise Exception(f"Error en el caso de uso GetEmployeeTimeOffRequests: {str(e)}")
