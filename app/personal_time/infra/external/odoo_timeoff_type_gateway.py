from typing import List, Optional
from datetime import date
from app.personal_time.domain.odoo_timeoff_gateway import OdooTimeOffGateway
from app.personal_time.domain.models import (
    TimeOffType,
    TimeOffRequest,
    TimeOffRequestResult,
    TimeOffRequestInfo,
)
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooTimeOffeGateway(OdooTimeOffGateway):
    """Implementación del gateway para tipos de licencias usando Odoo."""

    def __init__(self, odoo_connection: OdooConnection):
        """Inicializa el gateway con la conexión a Odoo.

        Args:
            odoo_connection: Conexión autenticada a Odoo
        """
        self.odoo_connection = odoo_connection

    def get_all_timeoff_types(self, employee_id: int) -> List[TimeOffType]:
        """Obtiene todos los tipos de licencias desde Odoo.

        Returns:
            List[TimeOffType]: Lista de tipos de licencias disponibles

        Raises:
            Exception: Si hay un error al conectar con Odoo o procesar los datos
        """
        domain = [
            "|",
            ["requires_allocation", "=", "no"],
            "&",
            ["has_valid_allocation", "=", True],
            "|",
            ["allows_negative", "=", True],
            "&",
            ["virtual_remaining_leaves", ">=", 0],
            ["allows_negative", "=", False],
        ]

        context = {
            "employee_id": employee_id,
            "lang": "es_AR",
        }

        try:
            # Ejecutar la consulta a Odoo usando el modelo hr.leave.type
            result = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave.type",
                "search_read",
                [domain],
                {
                    "fields": [
                        "id",
                        "name",
                        "virtual_remaining_leaves",
                        "requires_allocation",
                        "has_valid_allocation",
                        "allows_negative",
                    ],
                    "context": context,
                },
            )
            print(result)
            # Validar que el resultado sea una lista
            if not isinstance(result, list):
                raise Exception("Respuesta inesperada de Odoo: se esperaba una lista")

            # Convertir los datos de Odoo a nuestros modelos de dominio
            timeoff_types = [TimeOffType.from_odoo_data(item) for item in result]

            return timeoff_types

        except Exception as e:
            raise Exception(f"Error al obtener tipos de licencias desde Odoo: {str(e)}")

    def create_timeoff_request(
        self, timeoff_request: TimeOffRequest
    ) -> TimeOffRequestResult:
        """Crea una nueva solicitud de licencia en Odoo con el estado especificado.

        Args:
            timeoff_request: Solicitud de licencia a crear

        Returns:
            TimeOffRequestResult: Resultado de la operación con ID si es exitosa.
            Si la creación fue exitosa pero el cambio de estado falló, retorna éxito
            con un mensaje de advertencia.

        Raises:
            Exception: Si hay errores de comunicación con Odoo o errores del sistema durante la creación
        """
        request_id = None
        try:
            # Convertir la solicitud al formato esperado por Odoo
            # NO incluir el estado en el create - se aplicará después
            odoo_data = timeoff_request.to_odoo_data(include_state=False)
            
            # Guardar el estado deseado del objeto
            desired_state = timeoff_request.state

            # Ejecutar la creación en Odoo usando el modelo hr.leave
            # Se crea en estado draft por defecto
            request_id = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave",
                "create",
                [odoo_data],
            )

            # Validar que el ID retornado sea válido
            if not isinstance(request_id, int) or request_id <= 0:
                raise Exception(f"Respuesta inválida de Odoo: ID={request_id}")

            # Aplicar el estado deseado si se especificó y no es draft (que ya lo está)
            if desired_state and desired_state != "draft":
                try:
                    self.set_timeoff_request_state(request_id, desired_state)
                    return TimeOffRequestResult.success_result(request_id)
                except Exception as state_error:
                    # Si falla el cambio de estado, retornar éxito con advertencia
                    # La solicitud fue creada exitosamente pero quedó en estado draft
                    warning_msg = (
                        f"Creada en estado 'draft' - No se pudo cambiar a '{desired_state}': {str(state_error)}"
                    )
                    return TimeOffRequestResult(
                        success=True,
                        request_id=request_id,
                        message=warning_msg,
                        actual_state="draft",
                        desired_state=desired_state
                    )

            return TimeOffRequestResult.success_result(request_id)

        except Exception as e:
            # Si falla la creación (no el cambio de estado), propagar el error
            if request_id is None:
                raise
            # Si llegamos aquí, es un error después de crear pero antes del cambio de estado
            raise
    
    def set_timeoff_request_state(self, request_id: int, state: str):
        """Cambia el estado de una solicitud de licencia en Odoo.
        
        Args:
            request_id: ID de la solicitud en Odoo
            state: Estado deseado (draft, confirm, validate, refuse, cancel)
            
        Raises:
            Exception: Si hay un error al cambiar el estado
        """
        try:
            
            if state == "validate":
                self.odoo_connection["models"].execute_kw(
                    self.odoo_connection["ODOO_DB"],
                    self.odoo_connection["uid"],
                    self.odoo_connection["ODOO_PASSWORD"],
                    "hr.leave",
                    "action_approve",
                    [[request_id]],
                )
            elif state == "refuse":
                # Rechazar la solicitud
                self.odoo_connection["models"].execute_kw(
                    self.odoo_connection["ODOO_DB"],
                    self.odoo_connection["uid"],
                    self.odoo_connection["ODOO_PASSWORD"],
                    "hr.leave",
                    "action_refuse",
                    [[request_id]],
                )
            elif state == "draft":
                # Ya se crea en draft por defecto, no hacer nada
                pass
            
            else:
                raise ValueError(f"Estado no soportado: {state}")
                
        except Exception as e:
            raise Exception(f"Error al cambiar estado de solicitud a '{state}': {str(e)}")

    def update_timeoff_request(
        self, request_id: int, timeoff_request: TimeOffRequest
    ) -> TimeOffRequestResult:
        """Edita una solicitud de licencia existente en Odoo.

        Args:
            request_id: ID de la solicitud a editar
            timeoff_request: Datos actualizados de la solicitud

        Returns:
            TimeOffRequestResult: Resultado de la operación

        Raises:
            Exception: Si hay errores de comunicación con Odoo o errores del sistema
        """
        try:
            # Convertir la solicitud al formato esperado por Odoo
            odoo_data = timeoff_request.to_odoo_data()

            # Ejecutar la actualización en Odoo usando el modelo hr.leave
            success = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave",
                "write",
                [[request_id], odoo_data],
            )

            # Validar que la operación fue exitosa
            if not success:
                raise Exception(f"Error al actualizar la solicitud ID {request_id}")

            return TimeOffRequestResult.success_result(request_id)

        except Exception as e:
            # Propagar directamente el error original
            raise

    def get_timeoff_request_state(self, request_id: int) -> str:
        """Obtiene el estado de una solicitud de tiempo personal específica desde Odoo.

        Args:
            request_id: ID de la solicitud de tiempo personal

        Returns:
            str: Estado de la solicitud (draft, validate, refuse, cancel)

        Raises:
            Exception: Si hay un error al conectar con Odoo o procesar los datos
            ValueError: Si la solicitud no existe
        """
        try:
            # Ejecutar la consulta a Odoo usando el modelo hr.leave
            result = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave",
                "search_read",
                [[["id", "=", request_id]]],
                {
                    "fields": ["id", "state"],
                },
            )

            # Validar que el resultado sea una lista
            if not isinstance(result, list):
                raise Exception("Respuesta inesperada de Odoo: se esperaba una lista")

            # Verificar que se encontró la solicitud
            if not result:
                raise ValueError(f"No se encontró la solicitud con ID {request_id}")

            # Retornar el estado de la solicitud
            return result[0]["state"]

        except Exception as e:
            raise Exception(
                f"Error al obtener el estado de la solicitud desde Odoo: {str(e)}"
            )

    def get_employee_timeoff_requests(
        self,
        employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
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
                "number_of_days",
            ]

            # Filtro base: solicitudes del empleado especificado
            domain = [["employee_id", "=", employee_id]]

            if date_from and date_to:
                domain.append(
                    ["request_date_from", ">=", date_from.strftime("%Y-%m-%d")]
                )
                domain.append(["request_date_to", "<=", date_to.strftime("%Y-%m-%d")])

            # Ejecutar la consulta a Odoo usando el modelo hr.leave
            result = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave",
                "search_read",
                [domain],  # El dominio debe estar dentro de una lista
                {
                    "fields": fields,
                    "order": "request_date_from desc",
                },  # Ordenar por fecha más reciente primero
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
                    print(
                        f"Warning: Error procesando solicitud ID {item.get('id', 'unknown')}: {str(e)}"
                    )
                    continue

            return timeoff_requests

        except Exception as e:
            raise Exception(
                f"Error al obtener solicitudes de tiempo personal desde Odoo: {str(e)}"
            )

    def get_timeoff_type_by_name(self, name: str) -> Optional[TimeOffType]:
        """Busca un tipo de licencia por su nombre exacto en Odoo.
        
        Args:
            name: Nombre del tipo de licencia a buscar
            
        Returns:
            Optional[TimeOffType]: Tipo de licencia encontrado o None
            
        Raises:
            Exception: Si hay un error al consultar Odoo
        """
        try:
            # Buscar el tipo de licencia por nombre exacto
            domain = [["name", "=", name]]
            
            result = self.odoo_connection["models"].execute_kw(
                self.odoo_connection["ODOO_DB"],
                self.odoo_connection["uid"],
                self.odoo_connection["ODOO_PASSWORD"],
                "hr.leave.type",
                "search_read",
                [domain],
                {
                    "fields": [
                        "id",
                        "name",
                        "virtual_remaining_leaves",
                        "requires_allocation",
                        "has_valid_allocation",
                        "allows_negative",
                    ],
                },
            )
            
            # Validar que el resultado sea una lista
            if not isinstance(result, list):
                raise Exception("Respuesta inesperada de Odoo: se esperaba una lista")
            
            # Si no se encontró, retornar None
            if not result:
                return None
            
            # Convertir el primer resultado a modelo de dominio
            return TimeOffType.from_odoo_data(result[0])
            
        except Exception as e:
            raise Exception(f"Error al buscar tipo de licencia por nombre en Odoo: {str(e)}")