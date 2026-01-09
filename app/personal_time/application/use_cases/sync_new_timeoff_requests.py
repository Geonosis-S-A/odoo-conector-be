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
from app.personal_time.domain.gateway import TimeOffGateway
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
        self.skipped_count = 0  # Ya existían en la BD
    
    def add_success(self):
        """Registra una sincronización exitosa."""
        self.total_processed += 1
        self.successfully_synced += 1
    
    def add_error(self, humand_request_id: str, error_message: str):
        """Registra un error."""
        self.total_processed += 1
        self.errors_count += 1
        self.errors.append((humand_request_id, error_message))
    
    def add_skipped(self):
        """Registra una solicitud que se saltó (ya existía)."""
        self.total_processed += 1
        self.skipped_count += 1
    
    def get_summary(self) -> str:
        """Retorna un resumen de la sincronización."""
        return (
            f"Total procesadas: {self.total_processed}, "
            f"Sincronizadas: {self.successfully_synced}, "
            f"Saltadas: {self.skipped_count}, "
            f"Errores: {self.errors_count}"
        )


class SyncNewTimeOffRequestsUseCase:
    """
    Caso de uso para sincronizar nuevas solicitudes de licencias desde Humand a Odoo.
    
    Este use case consulta las licencias creadas en Humand desde la última ejecución
    exitosa, las inserta en Odoo y registra el mapeo de IDs en la Bridge Table.
    """
    
    def __init__(
        self,
        humand_gateway: HumandGateway,
        odoo_gateway: TimeOffGateway,
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
    
    def execute(
        self,
        created_at_since: Optional[datetime] = None
    ) -> SyncResult:
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
        
        logger.info(
            f"Iniciando sincronización de nuevas solicitudes desde: "
            f"{created_at_since or 'inicio'}"
        )
        
        try:
            # 1. Obtener nuevas solicitudes desde Humand
            humand_requests = self._fetch_new_requests_from_humand(
                created_at_since
            )
            
            logger.info(f"Obtenidas {len(humand_requests)} solicitudes desde Humand")
            
            # 2. Procesar cada solicitud
            for humand_request in humand_requests:
                self._process_single_request(humand_request, result)
            
            logger.info(f"Sincronización completada: {result.get_summary()}")
            
        except Exception as e:
            logger.error(f"Error general en la sincronización: {str(e)}")
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
            # Filtrar solo solicitudes aprobadas (fuente de verdad)
            # Puedes ajustar los estados según tus necesidades
            states = ["approved"]
            
            # Convertir datetime a date si es necesario
            created_date = created_at_since.date() if created_at_since else None
            
            requests = self.humand_gateway.get_all_timeoff_requests(
                page=1,
                states=states,
                created_at_since=created_date,
            )
            
            return requests
            
        except Exception as e:
            logger.error(f"Error al obtener solicitudes desde Humand: {str(e)}")
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
                logger.debug(
                    f"Solicitud {humand_request.id} ya existe, saltando..."
                )
                result.add_skipped()
                return
            
            # 2. Obtener el employee_id de Odoo usando el email
            employee = self.employee_gateway.get_by_email(humand_request.user_email)
            
            if not employee:
                error_msg = f"Empleado no encontrado en Odoo para email: {humand_request.user_email}"
                logger.warning(error_msg)
                result.add_error(humand_request.id, error_msg)
                return
            
            # 3. Mapear el tipo de licencia de Humand a Odoo
            # NOTA: Aquí necesitas implementar tu lógica de mapeo
            # Por ahora, usamos un ID por defecto o puedes crear un método
            odoo_holiday_status_id = self._map_policy_type_to_odoo(
                humand_request.policy_type_id, humand_request.policy_type_name
            )
            
            if not odoo_holiday_status_id:
                error_msg = f"No se pudo mapear tipo de licencia: {humand_request.policy_type_name}"
                logger.warning(error_msg)
                result.add_error(humand_request.id, error_msg)
                return
            
            # 4. Crear la solicitud en Odoo
            odoo_request = TimeOffRequest(
                holiday_status_id=odoo_holiday_status_id,
                name=humand_request.reason or f"Licencia desde Humand: {humand_request.policy_type_name}",
                request_date_from=humand_request.from_date,
                request_date_to=humand_request.to_date,
                employee_id=employee.id,
            )
            
            odoo_result = self.odoo_gateway.create_timeoff_request(odoo_request)
            
            if not odoo_result.success or not odoo_result.request_id:
                error_msg = f"Error al crear en Odoo: {odoo_result.message}"
                logger.warning(error_msg)
                result.add_error(humand_request.id, error_msg)
                return
            
            # 5. Crear el mapeo en la Bridge Table
            mapping = TimeOffSyncMapping.from_humand_and_odoo(
                humand_request=humand_request,
                odoo_request_id=odoo_result.request_id,
                odoo_employee_id=employee.id,
            )
            
            self.mapping_repository.save(mapping)
            
            logger.info(
                f"Solicitud sincronizada: Humand ID {humand_request.id} -> "
                f"Odoo ID {odoo_result.request_id}"
            )
            result.add_success()
            
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(
                f"Error procesando solicitud {humand_request.id}: {error_msg}"
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
                logger.debug(
                    f"Tipo de licencia mapeado: '{policy_type_name}' -> ID {timeoff_type.id}"
                )
                return timeoff_type.id
            
            logger.warning(
                f"No se encontró tipo de licencia en Odoo con nombre: '{policy_type_name}'"
            )
            return None
            
        except Exception as e:
            logger.error(
                f"Error al mapear tipo de licencia '{policy_type_name}': {str(e)}"
            )
            return None
