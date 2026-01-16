"""
Use Case para sincronizar nuevas solicitudes de licencias desde Humand a Odoo.

Este caso de uso implementa el sub-proceso de "Ingesta de Nuevas Licencias",
consultando las licencias creadas posteriormente al último job exitoso y
creándolas en Odoo mientras mantiene el mapeo de IDs.
"""

from typing import List, Optional, Tuple
from datetime import datetime
import logging
from app.personal_time.domain.humand_gateway import HumandGateway
from app.personal_time.domain.odoo_timeoff_gateway import OdooTimeOffGateway
from app.personal_time.domain.repositories import TimeOffSyncMappingRepository
from app.personal_time.domain.models import (
    HumandTimeOffRequest,
    TimeOffRequest,
    TimeOffSyncMapping,
)
from app.users.domain.repositories import EmployeeGateway


logger = logging.getLogger(__name__)


class SyncResult:
    """Resultado de la sincronización de nuevas solicitudes."""

    def __init__(self):
        self.total_processed = 0
        self.successfully_synced = 0
        self.errors_count = 0
        self.errors: List[Tuple[str, str]] = []  # (humand_request_id, error_message)
        self.successes: List[Tuple[str, dict]] = []  # (humand_request_id, details)
        self.skipped_count = 0  # Ya existían en la BD
        self.status_updates_count = 0  # Estados actualizados
        self.status_updates: List[Tuple[str, dict]] = []  # (humand_request_id, details)

    def add_success(self, humand_request_id: str, details: dict):
        """Registra una sincronización exitosa."""
        self.total_processed += 1
        self.successfully_synced += 1
        self.successes.append((humand_request_id, details))

    def add_error(self, humand_request_id: str, error_message: str):
        """Registra un error."""
        self.total_processed += 1
        self.errors_count += 1
        self.errors.append((humand_request_id, error_message))

    def add_skipped(self):
        """Registra una solicitud que se saltó (ya existía)."""
        self.total_processed += 1
        self.skipped_count += 1

    def add_status_update(self, humand_request_id: str, details: dict):
        """Registra una actualización de estado exitosa."""
        self.total_processed += 1
        self.status_updates_count += 1
        self.status_updates.append((humand_request_id, details))

    def get_summary(self) -> str:
        """Retorna un resumen de la sincronización."""
        return (
            f"Total procesadas: {self.total_processed}, "
            f"Sincronizadas: {self.successfully_synced}, "
            f"Actualizadas: {self.status_updates_count}, "
            f"Saltadas: {self.skipped_count}, "
            f"Errores: {self.errors_count}"
        )

    def to_dict(self) -> dict:
        """Convierte el resultado a un diccionario para serialización."""
        return {
            "total_processed": self.total_processed,
            "successfully_synced": self.successfully_synced,
            "status_updates_count": self.status_updates_count,
            "skipped": self.skipped_count,
            "errors_count": self.errors_count,
            "errors": [{"humand_id": err[0], "error": err[1]} for err in self.errors],
            "successes": [
                {"humand_id": success[0], **success[1]} for success in self.successes
            ],
            "status_updates": [
                {"humand_id": update[0], **update[1]} for update in self.status_updates
            ],
        }


class SyncNewTimeOffRequestsUseCase:
    """
    Caso de uso para sincronizar nuevas solicitudes de licencias desde Humand a Odoo.

    Este use case consulta las licencias creadas en Humand desde la última ejecución
    exitosa, las inserta en Odoo y registra el mapeo de IDs en la Bridge Table.
    """

    def __init__(
        self,
        humand_gateway: HumandGateway,
        odoo_gateway: OdooTimeOffGateway,
        employee_gateway: EmployeeGateway,
        mapping_repository: TimeOffSyncMappingRepository,
    ):
        """
        Inicializa el caso de uso con sus dependencias.

        Args:
            humand_gateway: Gateway para acceder a la API de Humand
            odoo_gateway: Gateway para acceder a Odoo
            employee_gateway: Gateway para acceder a empleados (mapeo email -> ID)
            mapping_repository: Repositorio para la tabla de mapeo
        """
        self.humand_gateway = humand_gateway
        self.odoo_gateway = odoo_gateway
        self.employee_gateway = employee_gateway
        self.mapping_repository = mapping_repository

    @staticmethod
    def build_run_details(
        new_requests_result: Optional["SyncResult"] = None,
        status_updates_result: Optional["SyncResult"] = None,
    ) -> dict:
        """
        Construye el JSON de detalles de una ejecución de sincronización.

        Args:
            new_requests_result: Resultado de la sincronización de nuevas solicitudes
            status_updates_result: Resultado de la sincronización de estados

        Returns:
            dict: Diccionario con los detalles completos de la ejecución
        """
        new_dict = (
            new_requests_result.to_dict()
            if new_requests_result
            else {
                "total_processed": 0,
                "successfully_synced": 0,
                "status_updates_count": 0,
                "skipped": 0,
                "errors_count": 0,
                "errors": [],
                "successes": [],
                "status_updates": [],
            }
        )

        status_dict = (
            status_updates_result.to_dict()
            if status_updates_result
            else {
                "total_processed": 0,
                "successfully_synced": 0,
                "status_updates_count": 0,
                "skipped": 0,
                "errors_count": 0,
                "errors": [],
                "successes": [],
                "status_updates": [],
            }
        )

        total_processed = new_dict["total_processed"] + status_dict["total_processed"]
        total_synced = (
            new_dict["successfully_synced"] + status_dict["status_updates_count"]
        )
        total_errors = new_dict["errors_count"] + status_dict["errors_count"]

        return {
            "new_requests": new_dict,
            "status_updates": status_dict,
            "summary": {
                "total_processed": total_processed,
                "total_synced": total_synced,
                "total_errors": total_errors,
            },
        }

    def execute(self, created_at_since: Optional[datetime] = None) -> SyncResult:
        """
        Ejecuta la sincronización de nuevas solicitudes.

        Args:
            created_at_since: Fecha desde la cual buscar nuevas solicitudes.
                            Si es None, busca todas las solicitudes.
            max_requests: Número máximo de solicitudes a procesar en esta ejecución

        Returns:
            SyncResult: Resultado de la sincronización con métricas
        """
        result = SyncResult()

        try:
            humand_requests = self._fetch_new_requests_from_humand(created_at_since)

            # 2. Procesar cada solicitud
            for humand_request in humand_requests:
                self._process_single_request(humand_request, result)

        except Exception as e:
            raise

        return result

    def execute_status_sync(
        self, resolution_from_date: Optional[datetime] = None
    ) -> SyncResult:
        """
        Ejecuta la sincronización de estados de solicitudes modificadas en Humand.

        Este método detecta las solicitudes que han cambiado de estado en Humand
        (usando el parámetro resolutionFromDate) y actualiza sus estados en Odoo
        utilizando la tabla de mapeo previamente poblada.

        Args:
            resolution_from_date: Fecha desde la cual buscar solicitudes resueltas/modificadas.
                                Si es None, busca todas las solicitudes.

        Returns:
            SyncResult: Resultado de la sincronización con métricas de actualizaciones
        """
        result = SyncResult()

        try:
            # 1. Obtener solicitudes modificadas desde Humand
            resolution_date = (
                resolution_from_date.date() if resolution_from_date else None
            )

            humand_requests = self.humand_gateway.get_all_timeoff_requests(
                resolution_from_date=resolution_date
            )

            # 2. Procesar cada solicitud para actualizar su estado
            for humand_request in humand_requests:
                self._process_single_status_update(humand_request, result)

        except Exception as e:
            raise

        return result

    def _fetch_new_requests_from_humand(
        self, created_at_since: Optional[datetime]
    ) -> List[HumandTimeOffRequest]:
        """
        Obtiene las nuevas solicitudes desde Humand.

        Args:
            created_at_since: Fecha desde la cual buscar
            max_requests: Número máximo de solicitudes

        Returns:
            List[HumandTimeOffRequest]: Lista de solicitudes desde Humand
        """
        try:
            created_date = created_at_since.date() if created_at_since else None

            requests = self.humand_gateway.get_all_timeoff_requests(
                created_at_since=created_date,
            )

            return requests

        except Exception as e:
            raise Exception(f"Error al consultar Humand API: {str(e)}")

    def _process_single_request(
        self, humand_request: HumandTimeOffRequest, result: SyncResult
    ):
        """
        Procesa una solicitud individual de Humand.

        Args:
            humand_request: Solicitud desde Humand
            result: Objeto para acumular resultados
        """
        try:
            # 1. Verificar si ya existe en la BD
            if self.mapping_repository.exists_by_humand_id(humand_request.id):
                result.add_skipped()
                return

            employee = self.employee_gateway.get_by_email(humand_request.user_email)

            if not employee:
                error_msg = (
                    f"Empleado no encontrado en Odoo | "
                    f"Email: {humand_request.user_email} | "
                    f"Nombre: {humand_request.user_name} | "
                    f"Humand User ID: {humand_request.user_id}"
                )
                result.add_error(humand_request.id, error_msg)
                return

            odoo_holiday_status_id = self._map_policy_type_to_odoo(
                humand_request.policy_type_id, humand_request.policy_type_name
            )

            if not odoo_holiday_status_id:
                error_msg = (
                    f"No se pudo mapear tipo de licencia | "
                    f"Tipo en Humand: '{humand_request.policy_type_name}' | "
                    f"ID Humand: {humand_request.policy_type_id} | "
                    f"Sugerencia: Verificar que el tipo de licencia existe en Odoo con ese nombre exacto"
                )
                result.add_error(humand_request.id, error_msg)
                return

            # Mapear el estado de Humand a Odoo
            odoo_state = self._map_humand_state_to_odoo(humand_request.status)

            odoo_request = TimeOffRequest(
                holiday_status_id=odoo_holiday_status_id,
                name=humand_request.reason
                or f"Licencia desde Humand: {humand_request.policy_type_name}",
                request_date_from=humand_request.from_date,
                request_date_to=humand_request.to_date,
                employee_id=employee.id,
                state=odoo_state,  # Estado mapeado desde Humand
            )

            odoo_result = self.odoo_gateway.create_timeoff_request(odoo_request)

            if not odoo_result.success or not odoo_result.request_id:
                error_msg = (
                    f"Error al crear en Odoo | "
                    f"Mensaje: {odoo_result.message} | "
                    f"Usuario: {humand_request.user_email} | "
                    f"Fechas: {humand_request.from_date} a {humand_request.to_date} | "
                    f"Tipo: {humand_request.policy_type_name}"
                )
                result.add_error(humand_request.id, error_msg)
                return

            # Siempre guardar el mapeo si se creó en Odoo
            mapping = TimeOffSyncMapping.from_humand_and_odoo(
                humand_request=humand_request,
                odoo_request_id=odoo_result.request_id,
                odoo_employee_id=employee.id,
            )

            self.mapping_repository.save(mapping)

            # Verificar si hubo problemas con el cambio de estado
            if (
                odoo_result.actual_state
                and odoo_result.desired_state
                and odoo_result.actual_state != odoo_result.desired_state
            ):
                # Se creó pero no se pudo cambiar al estado deseado
                error_msg = (
                    f"Creada en Odoo (ID: {odoo_result.request_id}) pero con estado incorrecto | "
                    f"Estado deseado: '{odoo_result.desired_state}' | "
                    f"Estado actual: '{odoo_result.actual_state}' | "
                    f"Motivo: {odoo_result.message} | "
                    f"Usuario: {humand_request.user_name} ({humand_request.user_email}) | "
                    f"Fechas: {humand_request.from_date} a {humand_request.to_date} | "
                    f"Tipo licencia: '{humand_request.policy_type_name}' (ID: {humand_request.policy_type_id}) | "
                    f"Estado Humand: {humand_request.status}"
                )
                result.add_error(humand_request.id, error_msg)
            else:
                # Sincronización exitosa - registrar detalles
                success_details = {
                    "odoo_request_id": odoo_result.request_id,
                    "user_email": humand_request.user_email,
                    "user_name": humand_request.user_name,
                    "from_date": humand_request.from_date.isoformat(),
                    "to_date": humand_request.to_date.isoformat(),
                    "policy_type": humand_request.policy_type_name,
                    "status": humand_request.status,
                    "odoo_state": odoo_state,
                }
                result.add_success(humand_request.id, success_details)

        except Exception as e:
            # Capturar información detallada del error
            import traceback
            from xmlrpc.client import Fault

            error_type = type(e).__name__
            error_detail = str(e)
            error_traceback = traceback.format_exc()

            # Si es un Fault de Odoo, extraer información específica
            if isinstance(e, Fault):
                fault_code = e.faultCode
                fault_string = e.faultString
                error_msg = (
                    f"Error de Odoo (Código {fault_code}) | "
                    f"Mensaje: {fault_string} | "
                    f"Humand ID: {humand_request.id} | "
                    f"Usuario: {humand_request.user_name} ({humand_request.user_email}) | "
                    f"Fechas: {humand_request.from_date} a {humand_request.to_date} | "
                    f"Tipo licencia: '{humand_request.policy_type_name}' (ID: {humand_request.policy_type_id}) | "
                    f"Estado Humand: {humand_request.status}"
                )
            else:
                error_msg = (
                    f"Error {error_type}: {error_detail} | "
                    f"Humand ID: {humand_request.id} | "
                    f"Usuario: {humand_request.user_name} ({humand_request.user_email}) | "
                    f"Fechas: {humand_request.from_date} a {humand_request.to_date} | "
                    f"Tipo licencia: '{humand_request.policy_type_name}' (ID: {humand_request.policy_type_id}) | "
                    f"Estado Humand: {humand_request.status}"
                )

            result.add_error(humand_request.id, error_msg)

    def _map_policy_type_to_odoo(
        self, policy_type_id: str, policy_type_name: str
    ) -> Optional[int]:
        """
        Mapea un tipo de política de Humand a un tipo de licencia en Odoo.

        El mapeo se realiza buscando en Odoo por el nombre exacto de la política,
        ya que los nombres en Humand y Odoo son idénticos.

        Args:
            policy_type_id: ID del tipo de política en Humand (no usado)
            policy_type_name: Nombre del tipo de política en Humand

        Returns:
            Optional[int]: ID del tipo de licencia en Odoo, o None si no se encuentra
        """
        try:
            # Buscar el tipo de licencia en Odoo por nombre exacto
            timeoff_type = self.odoo_gateway.get_timeoff_type_by_name(policy_type_name)

            if timeoff_type:
                return timeoff_type.id

            return None

        except Exception as e:
            return None

    def _map_humand_state_to_odoo(self, humand_state: str) -> str:
        """
        Mapea un estado de solicitud de Humand a un estado de Odoo.

        Humand States → Odoo States:
        - IN_PROGRESS → draft (esperando aprobación)
        - PENDING → draft (pendiente de aprobación)
        - APPROVED → validate (aprobado)
        - REJECTED → refuse (rechazado)
        - CANCELLED → refuse (rechazado)

        Args:
            humand_state: Estado de la solicitud en Humand

        Returns:
            str: Estado correspondiente en Odoo
        """
        state_mapping = {
            "IN_PROGRESS": "draft",  # En progreso → Esperando aprobación
            "PENDING": "draft",  # Pendiente → Esperando aprobación
            "APPROVED": "validate",  # Aprobado → Validado/Aprobado
            "REJECTED": "refuse",  # Rechazado → Rechazado
            "CANCELLED": "refuse",  # Cancelado → Rechazado
        }

        # Normalizar el estado (mayúsculas, sin espacios)
        normalized_state = humand_state.upper().strip()

        odoo_state = state_mapping.get(normalized_state, "draft")

        return odoo_state

    def _update_odoo_request_state(self, odoo_request_id: int, new_state: str) -> bool:
        """
        Actualiza solo el estado de una solicitud en Odoo.

        Args:
            odoo_request_id: ID de la solicitud en Odoo
            new_state: Nuevo estado a aplicar (confirm, validate, refuse)

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario
        """
        try:
            # Llamar al método del gateway que cambia el estado
            self.odoo_gateway.set_timeoff_request_state(odoo_request_id, new_state)

            return True

        except Exception as e:
            return False

    def _process_single_status_update(
        self, humand_request: HumandTimeOffRequest, result: SyncResult
    ):
        """
        Procesa la actualización de estado de una solicitud individual desde Humand.

        Args:
            humand_request: Solicitud desde Humand con estado potencialmente actualizado
            result: Objeto para acumular resultados
        """
        mapping = None  # Inicializar para evitar "possibly unbound"
        try:
            # 1. Buscar el mapping en la tabla de sincronización
            mapping = self.mapping_repository.get_by_humand_id(humand_request.id)

            if not mapping:
                result.add_skipped()
                return

            # 2. Obtener el estado actual desde Odoo
            try:
                current_odoo_state = self.odoo_gateway.get_timeoff_request_state(
                    mapping.odoo_request_id
                )
            except Exception as e:
                import traceback
                from xmlrpc.client import Fault

                error_type = type(e).__name__

                # Si es un Fault de Odoo, extraer información específica
                if isinstance(e, Fault):
                    fault_code = e.faultCode
                    fault_string = e.faultString
                    error_msg = (
                        f"Error de Odoo al obtener estado (Código {fault_code}) | "
                        f"Mensaje: {fault_string} | "
                        f"Odoo ID: {mapping.odoo_request_id} | "
                        f"Humand ID: {humand_request.id} | "
                        f"Usuario: {humand_request.user_name} ({humand_request.user_email})"
                    )
                else:
                    error_msg = (
                        f"Error al obtener estado desde Odoo | "
                        f"Tipo: {error_type} | "
                        f"Detalle: {str(e)} | "
                        f"Odoo ID: {mapping.odoo_request_id} | "
                        f"Humand ID: {humand_request.id} | "
                        f"Usuario: {humand_request.user_name} ({humand_request.user_email})"
                    )

                result.add_error(humand_request.id, error_msg)
                return

            # 3. Mapear el estado de Humand a Odoo
            desired_odoo_state = self._map_humand_state_to_odoo(humand_request.status)

            # 4. Comparar estados
            if current_odoo_state == desired_odoo_state:
                result.add_skipped()
                return

            # 5. Actualizar el estado en Odoo
            success = self._update_odoo_request_state(
                mapping.odoo_request_id, desired_odoo_state
            )

            if success:
                # Actualización de estado exitosa - registrar detalles
                update_details = {
                    "odoo_request_id": mapping.odoo_request_id,
                    "user_email": humand_request.user_email,
                    "user_name": humand_request.user_name,
                    "policy_type": humand_request.policy_type_name,
                    "previous_state": current_odoo_state,
                    "new_state": desired_odoo_state,
                    "humand_status": humand_request.status,
                }
                result.add_status_update(humand_request.id, update_details)
            else:
                error_msg = (
                    f"Error al actualizar estado en Odoo | "
                    f"Estado actual: '{current_odoo_state}' | "
                    f"Estado deseado: '{desired_odoo_state}' | "
                    f"Odoo ID: {mapping.odoo_request_id} | "
                    f"Humand ID: {humand_request.id} | "
                    f"Usuario: {humand_request.user_name} ({humand_request.user_email}) | "
                    f"Tipo licencia: '{humand_request.policy_type_name}' (ID: {humand_request.policy_type_id})"
                )
                result.add_error(humand_request.id, error_msg)

        except Exception as e:
            import traceback
            from xmlrpc.client import Fault

            error_type = type(e).__name__
            error_detail = str(e)
            error_traceback = traceback.format_exc()

            # Si es un Fault de Odoo, extraer información específica
            if isinstance(e, Fault):
                fault_code = e.faultCode
                fault_string = e.faultString
                error_msg = (
                    f"Error de Odoo al actualizar estado (Código {fault_code}) | "
                    f"Mensaje: {fault_string} | "
                    f"Humand ID: {humand_request.id} | "
                    f"Usuario: {humand_request.user_name} ({humand_request.user_email}) | "
                    f"Estado Humand: {humand_request.status} | "
                    f"Odoo ID: {mapping.odoo_request_id if mapping else 'N/A'}"
                )
            else:
                error_msg = (
                    f"Error al actualizar estado | "
                    f"Tipo: {error_type} | "
                    f"Detalle: {error_detail} | "
                    f"Humand ID: {humand_request.id} | "
                    f"Usuario: {humand_request.user_name} ({humand_request.user_email}) | "
                    f"Estado Humand: {humand_request.status} | "
                    f"Odoo ID: {mapping.odoo_request_id if mapping else 'N/A'}"
                )

            result.add_error(humand_request.id, error_msg)
