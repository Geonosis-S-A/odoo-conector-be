from typing import List, Optional
from datetime import date
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.domain.models import TimeOffType, TimeOffRequest, TimeOffRequestResult, TimeOffRequestInfo
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
            
        Raises:
            Exception: Si hay errores de comunicación con Odoo o errores del sistema
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
                raise Exception(f"Respuesta inválida de Odoo: ID={request_id}")
            
            return TimeOffRequestResult.success_result(request_id)
            
        except Exception as e:
            # Propagar la excepción para que el caso de uso y router puedan manejarla
            print(f"AAAAAAAAAAAAA Error al crear solicitud en Odoo: {str(e)}")
            raise Exception(f"Error al crear solicitud en Odoo: {str(e)}")

    def get_employee_timeoff_requests(
        self, 
        employee_id: int, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> List[TimeOffRequestInfo]:
        """Obtiene las solicitudes de tiempo personal de un empleado desde Odoo, opcionalmente filtradas por fechas.
        
        Args:
            employee_id: ID del empleado en Odoo
            date_from: Fecha de inicio del filtro (opcional)
            date_to: Fecha de fin del filtro (opcional)
            
        Returns:
            List[TimeOffRequestInfo]: Lista de solicitudes del empleado filtradas por fecha
            
        Raises:
            Exception: Si hay un error al conectar con Odoo o procesar los datos
            ValueError: Si los parámetros no son válidos
        """
        try:

            # Campos que necesitamos de hr.leave
            fields = [
                "id",
                "holiday_status_id",  # Relación con hr.leave.type
                "name",
                "request_date_from",
                "request_date_to", 
                "employee_id",  # Relación con hr.employee
                "state",
                "number_of_days"
            ]

            # Filtro base: solicitudes del empleado especificado
            domain = [["employee_id", "=", employee_id]]
            
            if date_from and date_to:
                domain.append(["request_date_from", ">=", date_from.strftime("%Y-%m-%d")])
                domain.append(["request_date_to", "<=", date_to.strftime("%Y-%m-%d")])

            # Ejecutar la consulta a Odoo usando el modelo hr.leave
            result = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave",
                "search_read",
                [domain],  # El dominio debe estar dentro de una lista
                {"fields": fields, "order": "request_date_from desc"}  # Ordenar por fecha más reciente primero
            )
            
            # Validar que el resultado sea una lista
            if not isinstance(result, list):
                raise Exception("Respuesta inesperada de Odoo: se esperaba una lista")
            
            # Convertir los datos de Odoo a nuestros modelos de dominio
            timeoff_requests = []
            for item in result:
                try:
                    timeoff_request_info = TimeOffRequestInfo.from_odoo_data(item)
                    timeoff_requests.append(timeoff_request_info)
                except Exception as e:
                    # Log the error but continue processing other records
                    print(f"Warning: Error procesando solicitud ID {item.get('id', 'unknown')}: {str(e)}")
                    continue
            
            return timeoff_requests
            
        except Exception as e:
            raise Exception(f"Error al obtener solicitudes de tiempo personal desde Odoo: {str(e)}")


