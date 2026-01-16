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
from app.personal_time.infra.external.odoo_timeoff_type_gateway import (
    OdooTimeOffeGateway,
)
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


# Zona horaria de Buenos Aires, Argentina
ARGENTINA_TZ = timezone("America/Argentina/Buenos_Aires")


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

        # Construir detalles usando el método del use case
        run_details = use_case.build_run_details(
            new_requests_result=new_requests_result,
            status_updates_result=status_updates_result,
        )

        # Agregar información del tipo de ejecución
        run_details["execution_type"] = "scheduled_job"

        # Calcular totales desde el summary
        total_errors = run_details["summary"]["total_errors"]
        sync_log.errors_count = total_errors
        sync_log.run_details = run_details

        # Determinar estado final
        total_synced = run_details["summary"]["total_synced"]

        if total_errors == 0 and total_synced > 0:
            sync_log.mark_as_success()
        elif total_errors > 0 and total_synced > 0:
            sync_log.mark_as_partial_success()
        else:
            sync_log.mark_as_error(
                sync_log.error_message
                or "Sincronización falló sin procesar solicitudes"
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
