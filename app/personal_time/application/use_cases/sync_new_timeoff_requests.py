"""
Use Case para sincronizar nuevas solicitudes de licencias desde Humand a Odoo.

Este caso de uso implementa el sub-proceso de "Ingesta de Nuevas Licencias",
consultando las licencias creadas posteriormente al último job exitoso y
creándolas en Odoo mientras mantiene el mapeo de IDs.
"""

from typing import Any, Dict, List, Optional, Tuple
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
        self.errors: List[Tuple[str, str]] = []
        self.skipped_count = 0
        self.status_updates_count = 0

        self.synced_details: List[Dict[str, Any]] = []
        self.skipped_details: List[Dict[str, Any]] = []
        self.status_update_details: List[Dict[str, Any]] = []
        self.error_details: List[Dict[str, Any]] = []

    def add_success(self, detail: Optional[Dict[str, Any]] = None):
        """Registra una sincronización exitosa."""
        self.total_processed += 1
        self.successfully_synced += 1
        if detail:
            self.synced_details.append(detail)

    def add_error(
        self,
        humand_request_id: str,
        error_message: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        """Registra un error."""
        self.total_processed += 1
        self.errors_count += 1
        self.errors.append((humand_request_id, error_message))
        if detail:
            self.error_details.append(detail)

    def add_skipped(self, detail: Optional[Dict[str, Any]] = None):
        """Registra una solicitud que se saltó (ya existía)."""
        self.total_processed += 1
        self.skipped_count += 1
        if detail:
            self.skipped_details.append(detail)

    def add_status_update(self, detail: Optional[Dict[str, Any]] = None):
        """Registra una actualización de estado exitosa."""
        self.total_processed += 1
        self.status_updates_count += 1
        if detail:
            self.status_update_details.append(detail)

    def get_summary(self) -> str:
        """Retorna un resumen de la sincronización."""
        return (
            f"Total procesadas: {self.total_processed}, "
            f"Sincronizadas: {self.successfully_synced}, "
            f"Actualizadas: {self.status_updates_count}, "
            f"Saltadas: {self.skipped_count}, "
            f"Errores: {self.errors_count}"
        )


# TODO: ALMACENAR CADA RUN DEL JOB EN LA TABLA DE LOG DE SINCRONIZACIONES
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
            # 1. Obtener solicitudes candidatas a cambio de estado desde Humand.
            # resolutionFromDate cubre cambios terminales (approved/rejected/cancelled),
            # pero no siempre detecta la primera aprobacion que mantiene la solicitud
            # en IN_PROGRESS y solo completa firstApprovalDate.
            humand_requests = self._fetch_status_sync_candidates(resolution_from_date)

            # 2. Procesar cada solicitud para actualizar su estado
            for humand_request in humand_requests:
                self._process_single_status_update(humand_request, result)

        except Exception as e:
            raise

        return result

    def _fetch_status_sync_candidates(
        self, resolution_from_date: Optional[datetime]
    ) -> List[HumandTimeOffRequest]:
        """Obtiene las solicitudes de Humand que pueden haber cambiado de estado."""
        resolution_date = resolution_from_date.date() if resolution_from_date else None

        # 1. Cambios terminales detectables por resolutionFromDate.
        resolved_requests = self.humand_gateway.get_all_timeoff_requests(
            resolution_from_date=resolution_date
        )

        # 2. Cambios intermedios hacia validate1. Humand mantiene estas licencias en
        # IN_PROGRESS y solo informa firstApprovalDate, por lo que no entran por
        # resolutionFromDate. Se reconsulta el universo de solicitudes en progreso
        # y luego se filtra a las que ya existen en el mapeo local.
        mapped_humand_ids = {
            mapping.humand_request_id
            for mapping in self.mapping_repository.get_all_synced()
        }
        in_progress_requests = [
            request
            for request in self.humand_gateway.get_all_timeoff_requests(
                states=["IN_PROGRESS"]
            )
            if request.id in mapped_humand_ids
        ]

        requests_by_id = {request.id: request for request in resolved_requests}
        for request in in_progress_requests:
            requests_by_id[request.id] = request

        return list(requests_by_id.values())

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

    def _build_error_detail(
        self, humand_request: HumandTimeOffRequest, error_message: str, error_type: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "humand_request_id": humand_request.id,
            "error_message": error_message,
            "error_type": error_type,
            "employee_name": humand_request.user_name,
            "employee_email": humand_request.user_email,
            "policy_type": humand_request.policy_type_name,
        }

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
            if self.mapping_repository.exists_by_humand_id(humand_request.id):
                result.add_skipped(detail={
                    "humand_request_id": humand_request.id,
                    "reason": "already_synced",
                })
                return

            employee = self.employee_gateway.get_by_email(humand_request.user_email)

            if not employee:
                error_msg = f"Empleado no encontrado en Odoo con email {humand_request.user_email}"
                result.add_error(
                    humand_request.id,
                    error_msg,
                    detail=self._build_error_detail(humand_request, error_msg, "employee_not_found"),
                )
                return

            odoo_holiday_status_id = self._map_policy_type_to_odoo(
                humand_request.policy_type_id, humand_request.policy_type_name
            )

            if not odoo_holiday_status_id:
                error_msg = f"Tipo de licencia '{humand_request.policy_type_name}' no encontrado en Odoo"
                result.add_error(
                    humand_request.id,
                    error_msg,
                    detail=self._build_error_detail(humand_request, error_msg, "policy_type_not_mapped"),
                )
                return

            odoo_state = self._map_humand_state_to_odoo(humand_request)

            odoo_request = TimeOffRequest(
                holiday_status_id=odoo_holiday_status_id,
                name=humand_request.reason
                or f"Licencia desde Humand: {humand_request.policy_type_name}",
                request_date_from=humand_request.from_date,
                request_date_to=humand_request.to_date,
                employee_id=employee.id,
                state=odoo_state,
            )

            odoo_result = self.odoo_gateway.create_timeoff_request(odoo_request)

            if not odoo_result.success or not odoo_result.request_id:
                error_msg = f"Error al crear en Odoo: {odoo_result.message}"
                result.add_error(
                    humand_request.id,
                    error_msg,
                    detail=self._build_error_detail(humand_request, error_msg, "odoo_create_failed"),
                )
                return

            mapping = TimeOffSyncMapping.from_humand_and_odoo(
                humand_request=humand_request,
                odoo_request_id=odoo_result.request_id,
                odoo_employee_id=employee.id,
            )

            self.mapping_repository.save(mapping)

            if (
                odoo_result.actual_state
                and odoo_result.desired_state
                and odoo_result.actual_state != odoo_result.desired_state
            ):
                error_msg = (
                    f"Creada en Odoo (ID: {odoo_result.request_id}) pero con estado incorrecto. "
                    f"Deseado: '{odoo_result.desired_state}', actual: '{odoo_result.actual_state}'. "
                    f"Motivo: {odoo_result.message}"
                )
                result.add_error(
                    humand_request.id,
                    error_msg,
                    detail=self._build_error_detail(humand_request, error_msg, "odoo_state_mismatch"),
                )
            else:
                result.add_success(detail={
                    "humand_request_id": humand_request.id,
                    "odoo_request_id": odoo_result.request_id,
                    "employee_name": humand_request.user_name,
                    "employee_email": humand_request.user_email,
                    "policy_type": humand_request.policy_type_name,
                    "from_date": str(humand_request.from_date),
                    "to_date": str(humand_request.to_date),
                    "humand_state": humand_request.status,
                    "odoo_state": odoo_state,
                })

        except Exception as e:
            from xmlrpc.client import Fault

            error_type = type(e).__name__

            if isinstance(e, Fault):
                error_msg = f"Error de Odoo (Código {e.faultCode}): {e.faultString}"
            else:
                error_msg = f"{error_type}: {str(e)}"

            result.add_error(
                humand_request.id,
                error_msg,
                detail=self._build_error_detail(humand_request, error_msg, error_type),
            )

    def _map_policy_type_to_odoo(
        self, policy_type_id: str, policy_type_name: str
    ) -> Optional[
        int
    ]:  # TODO: revisar mapeo por nombres de policy(funciona pero hay nombres que no coinciden).
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

    def _map_humand_state_to_odoo(self, humand_request: HumandTimeOffRequest) -> str:
        """
        Mapea un estado de solicitud de Humand a un estado de Odoo.

        Humand States → Odoo States:
        - PENDING → draft (todavía no enviada a aprobación)
        - IN_PROGRESS + firstApprovalDate null → confirm (pendiente de primera aprobación)
        - IN_PROGRESS + firstApprovalDate informado → validate1 (pendiente de segunda aprobación)
        - APPROVED → validate (aprobado)
        - REJECTED → refuse (rechazado)
        - CANCELLED → refuse (rechazado)

        Args:
            humand_request: Solicitud de Humand con su estado y metadata de aprobación

        Returns:
            str: Estado correspondiente en Odoo
        """
        state_mapping = {
            "PENDING": "draft",  # Pendiente de envío/confirmación
            "APPROVED": "validate",  # Aprobado → Validado/Aprobado
            "REJECTED": "refuse",  # Rechazado → Rechazado
            "CANCELLED": "refuse",  # Cancelado → Rechazado
        }

        # Normalizar el estado (mayúsculas, sin espacios)
        normalized_state = humand_request.status.upper().strip()

        if normalized_state == "IN_PROGRESS":
            if humand_request.first_approval_date:
                return "validate1"
            else:
                return "confirm"

        odoo_state = state_mapping.get(normalized_state, "draft")

        return odoo_state

    def _update_odoo_request_state(
        self, odoo_request_id: int, new_state: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Actualiza solo el estado de una solicitud en Odoo.

        Args:
            odoo_request_id: ID de la solicitud en Odoo
            new_state: Nuevo estado a aplicar (draft, confirm, validate1, validate, refuse)

        Returns:
            Tuple[bool, Optional[str]]: resultado y detalle de error si falla
        """
        try:
            # Llamar al método del gateway que cambia el estado
            self.odoo_gateway.set_timeoff_request_state(odoo_request_id, new_state)

            return True, None

        except Exception as e:
            return False, str(e)

    def _process_single_status_update(
        self, humand_request: HumandTimeOffRequest, result: SyncResult
    ):
        """
        Procesa la actualización de estado de una solicitud individual desde Humand.

        Args:
            humand_request: Solicitud desde Humand con estado potencialmente actualizado
            result: Objeto para acumular resultados
        """
        mapping = None
        try:
            mapping = self.mapping_repository.get_by_humand_id(humand_request.id)

            if not mapping:
                result.add_skipped(detail={
                    "humand_request_id": humand_request.id,
                    "reason": "no_mapping_found",
                })
                return

            try:
                current_odoo_state = self.odoo_gateway.get_timeoff_request_state(
                    mapping.odoo_request_id
                )
            except Exception as e:
                from xmlrpc.client import Fault
                error_type = type(e).__name__
                if isinstance(e, Fault):
                    error_msg = f"Error de Odoo al obtener estado (Código {e.faultCode}): {e.faultString}"
                else:
                    error_msg = f"Error al obtener estado desde Odoo: {str(e)}"

                result.add_error(
                    humand_request.id,
                    error_msg,
                    detail=self._build_error_detail(humand_request, error_msg, error_type),
                )
                return

            desired_odoo_state = self._map_humand_state_to_odoo(humand_request)

            if current_odoo_state == desired_odoo_state:
                result.add_skipped(detail={
                    "humand_request_id": humand_request.id,
                    "reason": "state_already_up_to_date",
                })
                return

            success, update_error = self._update_odoo_request_state(
                mapping.odoo_request_id, desired_odoo_state
            )

            if success:
                result.add_status_update(detail={
                    "humand_request_id": humand_request.id,
                    "odoo_request_id": mapping.odoo_request_id,
                    "employee_name": humand_request.user_name,
                    "employee_email": humand_request.user_email,
                    "policy_type": humand_request.policy_type_name,
                    "from_date": str(humand_request.from_date),
                    "to_date": str(humand_request.to_date),
                    "previous_odoo_state": current_odoo_state,
                    "new_odoo_state": desired_odoo_state,
                    "humand_state": humand_request.status,
                })
            else:
                error_msg = (
                    f"Error al actualizar estado en Odoo. "
                    f"Actual: '{current_odoo_state}', deseado: '{desired_odoo_state}'. "
                    f"Detalle: {update_error or 'Sin detalle adicional'}"
                )
                result.add_error(
                    humand_request.id,
                    error_msg,
                    detail=self._build_error_detail(humand_request, error_msg, "odoo_state_update_failed"),
                )

        except Exception as e:
            from xmlrpc.client import Fault

            error_type = type(e).__name__

            if isinstance(e, Fault):
                error_msg = f"Error de Odoo al actualizar estado (Código {e.faultCode}): {e.faultString}"
            else:
                error_msg = f"{error_type}: {str(e)}"

            result.add_error(
                humand_request.id,
                error_msg,
                detail=self._build_error_detail(humand_request, error_msg, error_type),
            )
