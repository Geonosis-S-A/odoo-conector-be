from typing import List
from app.personal_time.domain.gateway import LeaveTypeGateway
from app.personal_time.domain.models import LeaveType, LeaveRequest, LeaveRequestResult
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooLeaveTypeGateway(LeaveTypeGateway):
    """Implementación del gateway para tipos de licencias usando Odoo."""
    
    def __init__(self, odoo_connection: OdooConnection):
        """Inicializa el gateway con la conexión a Odoo.
        
        Args:
            odoo_connection: Conexión autenticada a Odoo
        """
        self.odoo_connection = odoo_connection
    
    def get_all_leave_types(self) -> List[LeaveType]:
        """Obtiene todos los tipos de licencias desde Odoo.
        
        Returns:
            List[LeaveType]: Lista de tipos de licencias disponibles
            
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
            leave_types = [LeaveType.from_odoo_data(item) for item in result]
            
            return leave_types
            
        except Exception as e:
            raise Exception(f"Error al obtener tipos de licencias desde Odoo: {str(e)}")

    def create_leave_request(self, leave_request: LeaveRequest) -> LeaveRequestResult:
        """Crea una nueva solicitud de licencia en Odoo.
        
        Args:
            leave_request: Solicitud de licencia a crear
            
        Returns:
            LeaveRequestResult: Resultado de la operación con ID si es exitosa
        """
        try:
            # Convertir la solicitud al formato esperado por Odoo
            odoo_data = leave_request.to_odoo_data()
            
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
                return LeaveRequestResult.error_result(
                    f"Respuesta inválida de Odoo: ID={request_id}"
                )
            
            return LeaveRequestResult.success_result(request_id)
            
        except Exception as e:
            return LeaveRequestResult.error_result(str(e))
