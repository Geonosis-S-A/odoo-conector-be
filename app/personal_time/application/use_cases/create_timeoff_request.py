from datetime import date
from typing import Optional
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.domain.models import TimeOffRequest, TimeOffRequestResult


class CreateTimeOffRequestUseCase:
    """Caso de uso para crear una nueva solicitud de licencia."""
    
    def __init__(self, timeoff_gateway: TimeOffGateway):
        """Inicializa el caso de uso con el gateway de tipos de licencias.
        
        Args:
            timeoff_gateway: Gateway para acceder a las operaciones de licencias
        """
        self.timeoff_gateway = timeoff_gateway
    
    def execute(
        self,
        employee_id: int,
        holiday_status_id: int,
        request_date_from: date,
        request_date_to: date,
        description: Optional[str] = None
    ) -> TimeOffRequestResult:
        """Ejecuta el caso de uso para crear una solicitud de licencia.
        
        Args:
            employee_id: ID del empleado que solicita la licencia
            holiday_status_id: ID del tipo de licencia
            request_date_from: Fecha de inicio de la licencia
            request_date_to: Fecha de fin de la licencia
            description: Descripción/motivo de la solicitud
            
        Returns:
            TimeOffRequestResult: Resultado de la operación con ID si es exitosa
            
        Raises:
            ValueError: Si los parámetros no son válidos
            Exception: Si hay un error al crear la solicitud
        """
        try:
            # Validaciones de negocio
            self._validate_input_parameters(
                employee_id, holiday_status_id, request_date_from, request_date_to, description
            )
            
            # Crear la solicitud
            timeoff_request = TimeOffRequest(
                holiday_status_id=holiday_status_id,
                name=description,
                request_date_from=request_date_from,
                request_date_to=request_date_to,
                employee_id=employee_id
            )
            
            # Delegar al gateway
            result = self.timeoff_gateway.create_timeoff_request(timeoff_request)
            
            return result
            
        except ValueError:
            # Re-propagar ValueError para que el router pueda manejarlo con HTTP 400
            raise
        except Exception as e:
            return TimeOffRequestResult.error_result(f"Error en el caso de uso CreateTimeOffRequest: {str(e)}")
    
    def _validate_input_parameters(
        self,
        employee_id: int,
        holiday_status_id: int,
        request_date_from: date,
        request_date_to: date,
        description: Optional[str]
    ) -> None:
        """Valida los parámetros de entrada.
        
        Args:
            employee_id: ID del empleado
            holiday_status_id: ID del tipo de licencia
            request_date_from: Fecha de inicio
            request_date_to: Fecha de fin
            description: Descripción
            
        Raises:
            ValueError: Si algún parámetro no es válido
        """
        # Validar IDs
        if not isinstance(employee_id, int) or employee_id <= 0:
            raise ValueError("employee_id debe ser un entero positivo")
        
        if not isinstance(holiday_status_id, int) or holiday_status_id <= 0:
            raise ValueError("holiday_status_id debe ser un entero positivo")
        
        # Validar fechas
        if not isinstance(request_date_from, date):
            raise ValueError("request_date_from debe ser una fecha válida")
        
        if not isinstance(request_date_to, date):
            raise ValueError("request_date_to debe ser una fecha válida")
        
        if request_date_from > request_date_to:
            raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")
        
        # Validar que las fechas no sean muy en el pasado (opcional)
        today = date.today()
        if request_date_to < today:
            raise ValueError("No se pueden crear solicitudes para fechas pasadas")
        
        if description and not description.strip():
            raise ValueError("description no puede estar vacía")
        
        if description and len(description.strip()) > 500:
            raise ValueError("description no puede exceder 500 caracteres")
    
    