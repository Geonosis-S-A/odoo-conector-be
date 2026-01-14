from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.shared.infra.db.session import get_db
import logging

from app.personal_time.api.schemas import SyncRunResponse

logger = logging.getLogger(__name__)


from app.personal_time.infra.external.odoo_timeoff_type_gateway import (
    OdooTimeOffeGateway,
)
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)

from app.personal_time.application.use_cases.sync_new_timeoff_requests import (
    SyncNewTimeOffRequestsUseCase,
)
from app.personal_time.domain.models import TimeOffSyncLog
from app.personal_time.infra.db.repositories import (
    SQLModelTimeOffSyncMappingRepository,
    SQLModelTimeOffSyncLogRepository,
)
from app.personal_time.infra.external.humand_gateway import HumandAPIGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


router = APIRouter(prefix="/timeoff", tags=["timeoff"])

def get_sync_use_case(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
    db: Session = Depends(get_db),
) -> SyncNewTimeOffRequestsUseCase:
    """Dependencia para obtener el use case de sincronización."""
    try:
        humand_gateway = HumandAPIGateway()
        odoo_gateway = OdooTimeOffeGateway(odoo_connection)
        employee_gateway = OdooEmployeeGateway(odoo_connection)
        mapping_repository = SQLModelTimeOffSyncMappingRepository(db)
        
        return SyncNewTimeOffRequestsUseCase(
            humand_gateway=humand_gateway,
            odoo_gateway=odoo_gateway,
            employee_gateway=employee_gateway,
            mapping_repository=mapping_repository,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al inicializar use case de sincronización: {str(e)}",
        )



@router.post("/sync", response_model=SyncRunResponse)
async def sync_timeoff_requests(
    use_case: SyncNewTimeOffRequestsUseCase = Depends(get_sync_use_case),
    db: Session = Depends(get_db),
):
    """
    Ejecuta la sincronización completa de solicitudes de licencias desde Humand a Odoo.
    
    Este endpoint ejecuta dos procesos secuenciales:
    1. Sincronización de nuevas solicitudes (creadas desde la última ejecución exitosa)
    2. Sincronización de estados (solicitudes modificadas desde la última ejecución exitosa)
    
    Cada ejecución se registra en la base de datos con un log completo que incluye:
    - Métricas de sincronización
    - Errores detallados
    - Información completa en formato JSON
    
    Returns:
        SyncRunResponse: Resultado de la sincronización con detalles completos
    """
    # Inicializar repositorio de logs
    log_repo = SQLModelTimeOffSyncLogRepository(db)
    
    # Obtener fecha de última ejecución exitosa
    last_successful_run = log_repo.get_last_successful_run()
    
    # Crear log inicial
    sync_log = TimeOffSyncLog.create_new_run(last_successful_run)
    sync_log = log_repo.save(sync_log)
    
    try:
        # 1. Sincronizar nuevas solicitudes
        new_requests_result = None
        status_updates_result = None
        
        try:
            new_requests_result = use_case.execute(created_at_since=last_successful_run)
            sync_log.new_requests_synced = new_requests_result.successfully_synced
        except Exception as e:
            logger.error(f"Error crítico en sincronización de nuevas solicitudes: {str(e)}", exc_info=True)
            error_msg = f"Error en sincronización de nuevas solicitudes: {str(e)}"
            sync_log.error_message = error_msg
        
        # 2. Sincronizar actualizaciones de estado (desde la última ejecución exitosa)
        try:
            status_updates_result = use_case.execute_status_sync(
                resolution_from_date=last_successful_run
            )
            sync_log.status_updates_synced = status_updates_result.status_updates_count
        except Exception as e:
            logger.error(f"Error crítico en sincronización de estados: {str(e)}", exc_info=True)
            error_msg = f"Error en sincronización de estados: {str(e)}"
            if sync_log.error_message:
                sync_log.error_message += f" | {error_msg}"
            else:
                sync_log.error_message = error_msg
        
        # Calcular total de errores
        total_errors = 0
        
        if new_requests_result:
            total_errors += new_requests_result.errors_count
        
        if status_updates_result:
            total_errors += status_updates_result.errors_count
        
        sync_log.errors_count = total_errors
        
        # Construir detalles completos en JSON
        run_details = {
            "new_requests": {
                "total_processed": new_requests_result.total_processed if new_requests_result else 0,
                "successfully_synced": new_requests_result.successfully_synced if new_requests_result else 0,
                "skipped": new_requests_result.skipped_count if new_requests_result else 0,
                "errors_count": new_requests_result.errors_count if new_requests_result else 0,
                "errors": [
                    {"humand_id": err[0], "error": err[1]}
                    for err in (new_requests_result.errors if new_requests_result else [])
                ],
            },
            "status_updates": {
                "total_processed": status_updates_result.total_processed if status_updates_result else 0,
                "status_updates_count": status_updates_result.status_updates_count if status_updates_result else 0,
                "skipped": status_updates_result.skipped_count if status_updates_result else 0,
                "errors_count": status_updates_result.errors_count if status_updates_result else 0,
                "errors": [
                    {"humand_id": err[0], "error": err[1]}
                    for err in (status_updates_result.errors if status_updates_result else [])
                ],
            },
            "summary": {
                "total_processed": (
                    (new_requests_result.total_processed if new_requests_result else 0) +
                    (status_updates_result.total_processed if status_updates_result else 0)
                ),
                "total_synced": (
                    (new_requests_result.successfully_synced if new_requests_result else 0) +
                    (status_updates_result.status_updates_count if status_updates_result else 0)
                ),
                "total_errors": total_errors,
            },
        }
        
        sync_log.run_details = run_details
        
        # Determinar estado final
        # Si hay un error_message establecido (por excepción en los try/except), es un error crítico
        if sync_log.error_message:
            sync_log.mark_as_error(sync_log.error_message)
            message = sync_log.error_message
        # Si no hay errores de procesamiento individual
        elif total_errors == 0:
            sync_log.mark_as_success()
            total_synced = (
                (new_requests_result.successfully_synced if new_requests_result else 0) +
                (status_updates_result.status_updates_count if status_updates_result else 0)
            )
            if total_synced > 0:
                message = f"Sincronización completada exitosamente: {total_synced} registro(s) procesado(s)"
            else:
                message = "Sincronización completada exitosamente: sin registros nuevos para procesar"
        # Si hay errores pero también se procesaron algunos registros exitosamente
        else:
            sync_log.mark_as_partial_success()
            message = f"Sincronización completada con {total_errors} error(es)"
        
        # Actualizar log en BD
        log_repo.update(sync_log)
        
        # Retornar respuesta
        return SyncRunResponse(
            run_id=sync_log.id or 0,
            status=sync_log.status,
            message=message,
            started_at=sync_log.started_at,
            finished_at=sync_log.finished_at,
            execution_time_seconds=sync_log.execution_time_seconds,
            new_requests_synced=sync_log.new_requests_synced,
            status_updates_synced=sync_log.status_updates_synced,
            errors_count=sync_log.errors_count,
            run_details=sync_log.run_details,
        )
        
    except Exception as e:
        # Error crítico - marcar como error
        error_msg = f"Error crítico en sincronización: {str(e)}"
        sync_log.mark_as_error(error_msg)
        sync_log.run_details = {
            "critical_error": str(e),
            "error_type": type(e).__name__,
        }
        log_repo.update(sync_log)
        
        raise HTTPException(
            status_code=500,
            detail=error_msg,
        )