"""
Job programado para sincronizar solicitudes de licencias de Humand a Odoo.

Este job se ejecuta automáticamente a las 18:00 hrs (horario de Buenos Aires, Argentina).
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from app.shared.infra.db.session import SessionLocal
from app.shared.infra.external.odoo.odoo_client import OdooClient
from app.personal_time.application.use_cases.sync_new_timeoff_requests import (
    SyncNewTimeOffRequestsUseCase,
)
from app.personal_time.domain.models import TimeOffSyncLog
from app.personal_time.infra.db.repositories import (
    SQLModelTimeOffSyncMappingRepository,
    SQLModelTimeOffSyncLogRepository,
)
from app.personal_time.infra.external.humand_gateway import HumandAPIGateway
from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.personal_time.api.schemas import (
    RunDetails,
    NewRequestsPhaseDetail,
    StatusUpdatesPhaseDetail,
    SyncSummary,
    SyncedRecordDetail,
    StatusUpdateRecordDetail,
    SkippedRecordDetail,
    ErrorRecordDetail,
)


# Zona horaria de Buenos Aires, Argentina
ARGENTINA_TZ = timezone('America/Argentina/Buenos_Aires')


def execute_timeoff_sync_job():
    """
    Ejecuta la sincronización de solicitudes de licencias.
    
    Esta función replica la lógica del endpoint /timeoff/sync pero
    se ejecuta de forma automática según el scheduler configurado.
    """
    db = SessionLocal()
    
    try:
        # Crear conexión a Odoo
        odoo_client = OdooClient()
        odoo_connection = odoo_client.get_connection()
        
        # Inicializar gateways y repositorios
        humand_gateway = HumandAPIGateway()
        odoo_gateway = OdooTimeOffeGateway(odoo_connection)
        employee_gateway = OdooEmployeeGateway(odoo_connection)
        mapping_repository = SQLModelTimeOffSyncMappingRepository(db)
        log_repo = SQLModelTimeOffSyncLogRepository(db)
        
        # Crear use case
        use_case = SyncNewTimeOffRequestsUseCase(
            humand_gateway=humand_gateway,
            odoo_gateway=odoo_gateway,
            employee_gateway=employee_gateway,
            mapping_repository=mapping_repository,
        )
        
        # Obtener fecha de última ejecución exitosa
        last_successful_run = log_repo.get_last_successful_run()
        
        # Crear log inicial
        sync_log = TimeOffSyncLog.create_new_run(last_successful_run)
        sync_log = log_repo.save(sync_log)
        
        # Ejecutar sincronización de nuevas solicitudes
        new_requests_result = None
        status_updates_result = None
        
        try:
            new_requests_result = use_case.execute(created_at_since=last_successful_run)
            sync_log.new_requests_synced = new_requests_result.successfully_synced
        except Exception as e:
            error_msg = f"Error en sincronización de nuevas solicitudes: {str(e)}"
            sync_log.errors_count += 1
            sync_log.error_message = error_msg
        
        # Ejecutar sincronización de estados
        try:
            status_updates_result = use_case.execute_status_sync(
                resolution_from_date=last_successful_run
            )
            sync_log.status_updates_synced = status_updates_result.status_updates_count
        except Exception as e:
            error_msg = f"Error en sincronización de estados: {str(e)}"
            sync_log.errors_count += 1
            if sync_log.error_message:
                sync_log.error_message += f" | {error_msg}"
            else:
                sync_log.error_message = error_msg
        
        # Calcular totales
        total_errors = 0
        if new_requests_result:
            total_errors += new_requests_result.errors_count
        if status_updates_result:
            total_errors += status_updates_result.errors_count
        
        sync_log.errors_count = total_errors
        
        run_details = RunDetails(
            new_requests=NewRequestsPhaseDetail(
                total_processed=new_requests_result.total_processed if new_requests_result else 0,
                successfully_synced=new_requests_result.successfully_synced if new_requests_result else 0,
                skipped=new_requests_result.skipped_count if new_requests_result else 0,
                errors_count=new_requests_result.errors_count if new_requests_result else 0,
                synced_records=[
                    SyncedRecordDetail(**d) for d in (new_requests_result.synced_details if new_requests_result else [])
                ],
                skipped_records=[
                    SkippedRecordDetail(**d) for d in (new_requests_result.skipped_details if new_requests_result else [])
                ],
                errors=[
                    ErrorRecordDetail(**d) for d in (new_requests_result.error_details if new_requests_result else [])
                ],
            ),
            status_updates=StatusUpdatesPhaseDetail(
                total_processed=status_updates_result.total_processed if status_updates_result else 0,
                status_updates_count=status_updates_result.status_updates_count if status_updates_result else 0,
                skipped=status_updates_result.skipped_count if status_updates_result else 0,
                errors_count=status_updates_result.errors_count if status_updates_result else 0,
                updated_records=[
                    StatusUpdateRecordDetail(**d) for d in (status_updates_result.status_update_details if status_updates_result else [])
                ],
                skipped_records=[
                    SkippedRecordDetail(**d) for d in (status_updates_result.skipped_details if status_updates_result else [])
                ],
                errors=[
                    ErrorRecordDetail(**d) for d in (status_updates_result.error_details if status_updates_result else [])
                ],
            ),
            summary=SyncSummary(
                total_processed=(
                    (new_requests_result.total_processed if new_requests_result else 0) +
                    (status_updates_result.total_processed if status_updates_result else 0)
                ),
                total_synced=(
                    (new_requests_result.successfully_synced if new_requests_result else 0) +
                    (status_updates_result.status_updates_count if status_updates_result else 0)
                ),
                total_errors=total_errors,
            ),
        )
        
        sync_log.run_details = run_details.model_dump(mode="json")
        
        # Determinar estado final
        if total_errors == 0 and (
            (new_requests_result and new_requests_result.successfully_synced > 0) or
            (status_updates_result and status_updates_result.status_updates_count > 0)
        ):
            sync_log.mark_as_success()
        elif total_errors > 0 and (
            (new_requests_result and new_requests_result.successfully_synced > 0) or
            (status_updates_result and status_updates_result.status_updates_count > 0)
        ):
            sync_log.mark_as_partial_success()
        else:
            sync_log.mark_as_error(
                sync_log.error_message or "Sincronización falló sin procesar solicitudes"
            )
        
        # Actualizar log en BD
        log_repo.update(sync_log)
        
    except Exception as e:
        # Intentar registrar el error en la BD
        try:
            log_repo = SQLModelTimeOffSyncLogRepository(db)
            last_successful_run = log_repo.get_last_successful_run()
            sync_log = TimeOffSyncLog.create_new_run(last_successful_run)
            sync_log.mark_as_error(f"Error crítico en job: {str(e)}")
            sync_log.run_details = {
                "critical_error": str(e),
                "error_type": type(e).__name__,
                "execution_type": "scheduled_job",
            }
            log_repo.save(sync_log)
        except:
            pass
        
    finally:
        db.close()


# Instancia global del scheduler con zona horaria de Buenos Aires
scheduler = BackgroundScheduler(timezone=ARGENTINA_TZ)


def start_scheduler():
    """
    Inicia el scheduler con los jobs configurados.
    
    Configura un job que se ejecuta diariamente a las 18:00 hrs (Buenos Aires, Argentina).
    """
    scheduler.add_job(
        func=execute_timeoff_sync_job,
        trigger=CronTrigger(hour=19, minute=00, timezone=ARGENTINA_TZ),
        id="timeoff_sync_daily",
        name="Sincronización diaria de licencias Humand → Odoo",
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.start()


def stop_scheduler():
    """Detiene el scheduler de forma segura."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
