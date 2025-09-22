from typing import List
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.domain.models import TimeOffType, TimeOffRequest, TimeOffRequestResult
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooTimeOffeGateway(TimeOffGateway):
    """Implementación del gateway para tipos de licencias usando Odoo."""
    
    def __init__(self, odoo_connection: OdooConnection):
        """Inicializa el gateway con la conexión a Odoo.
        
        Args:
            odoo_connection: Conexión autenticada a Odoo
        """
        self.odoo_connection = odoo_connection
    
    def get_all_timeoff_types(self) -> List[TimeOffType]:
        """Obtiene todos los tipos de licencias desde Odoo.
        
        Returns:
            List[TimeOffType]: Lista de tipos de licencias disponibles
            
        Raises:
            Exception: Si hay un error al conectar con Odoo o procesar los datos
        """
        try:
            # Ejecutar la consulta a Odoo usando el modelo hr.leave.type
            result = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave.type",
                "search_read",
                [[]],  # Sin filtros, obtener todos
                {"fields": ["id", "name"]}  # Solo campos necesarios
            )
            
            # Validar que el resultado sea una lista
            if not isinstance(result, list):
                raise Exception("Respuesta inesperada de Odoo: se esperaba una lista")
            
            # Convertir los datos de Odoo a nuestros modelos de dominio
            timeoff_types = [TimeOffType.from_odoo_data(item) for item in result]
            
            return timeoff_types
            
        except Exception as e:
            raise Exception(f"Error al obtener tipos de licencias desde Odoo: {str(e)}")

    def create_timeoff_request(self, timeoff_request: TimeOffRequest) -> TimeOffRequestResult:
        """Crea una nueva solicitud de licencia en Odoo.
        
        Args:
            timeoff_request: Solicitud de licencia a crear
            
        Returns:
            TimeOffRequestResult: Resultado de la operación con ID si es exitosa
        """
        try:
            # Convertir la solicitud al formato esperado por Odoo
            odoo_data = timeoff_request.to_odoo_data()
            
            # Ejecutar la creación en Odoo usando el modelo hr.leave
            request_id = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave",
                "create",
                [odoo_data]
            )
            
            # Validar que el ID retornado sea válido
            if not isinstance(request_id, int) or request_id <= 0:
                return TimeOffRequestResult.error_result(
                    f"Respuesta inválida de Odoo: ID={request_id}"
                )
            
            return TimeOffRequestResult.success_result(request_id)
            
        except Exception as e:
            return TimeOffRequestResult.error_result(str(e))
