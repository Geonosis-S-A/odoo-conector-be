from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlmodel import Session
from app.shared.infra.db.session import get_db

from app.personal_time.api.schemas import (
    TimeOffTypeResponse,
    TimeOffRequestCreate,
    TimeOffRequestUpdate,
    TimeOffRequestResponse,
    TimeOffRequestInfoResponse,
    SyncRunResponse,
)
from app.personal_time.application.use_cases.get_timeoff_types import (
    GetTimeOffTypesUseCase,
)
from app.personal_time.application.use_cases.create_timeoff_request import (
    CreateTimeOffRequestUseCase,
)
from app.personal_time.application.use_cases.update_timeoff_request import (
    UpdateTimeOffRequestUseCase,
)
from app.personal_time.application.use_cases.get_employee_timeoff_requests import (
    GetEmployeeTimeOffRequestsUseCase,
)
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.infra.external.odoo_timeoff_type_gateway import (
    OdooTimeOffeGateway,
)
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.shared.security.dependencies import get_current_user

from app.personal_time.application.use_cases.sync_new_timeoff_requests import (
    SyncNewTimeOffRequestsUseCase,
)
from app.personal_time.domain.repositories import TimeOffSyncLogRepository
from app.personal_time.domain.models import TimeOffSyncLog
from app.personal_time.infra.db.repositories import (
    SQLModelTimeOffSyncMappingRepository,
    SQLModelTimeOffSyncLogRepository,
)
from app.personal_time.infra.external.humand_gateway import HumandAPIGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway

import logging


router = APIRouter(prefix="/timeoff", tags=["timeoff"])


def get_timeoff_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TimeOffGateway:
    """Dependencia para obtener el gateway de tipos de licencias."""
    try:
        return OdooTimeOffeGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error al conectar con el gateway de tipos de licencias",
        )

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


@router.get("/types", response_model=List[TimeOffTypeResponse])
async def get_timeoff_types(
    gateway: TimeOffGateway = Depends(get_timeoff_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene todos los tipos de licencias disponibles en el sistema.

    Returns:
        List[TimeOffTypeResponse]: Lista de tipos de licencias disponibles
    """
    employee_id = current_user.get("user_id")
    if not employee_id:
        raise HTTPException(
            status_code=400,
            detail="No se pudo determinar el ID del empleado para el usuario actual",
        )
    try:
        use_case = GetTimeOffTypesUseCase(gateway)
        timeoff_types = use_case.execute(employee_id)

        return [
            TimeOffTypeResponse(
                id=timeoff_type.id,
                name=timeoff_type.name,
                virtual_remaining_leaves=timeoff_type.virtual_remaining_leaves,
                requires_allocation=timeoff_type.requires_allocation,
                has_valid_allocation=timeoff_type.has_valid_allocation,
                allows_negative=timeoff_type.allows_negative,
            )
            for timeoff_type in timeoff_types
        ]
    except ValueError as e:
        # Errores de validación → HTTP 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Errores de Odoo/negocio → HTTP 400 (datos rechazados por reglas de negocio)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=TimeOffRequestResponse)
async def create_timeoff_request(
    request_data: TimeOffRequestCreate,
    gateway: TimeOffGateway = Depends(get_timeoff_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Crea una nueva solicitud de tiempo personal en el sistema.

    Args:
        request_data: Datos de la solicitud de tiempo personal
        gateway: Gateway para operaciones de tiempo personal
        current_user: Usuario autenticado actual

    Returns:
        TimeOffRequestResponse: Resultado de la operación con ID si es exitosa

    Raises:
        HTTPException: Si hay errores en la validación o creación
    """
    try:
        # Obtener el employee_id del usuario autenticado
        # Nota: Asumimos que el user_id corresponde al employee_id en Odoo
        # En un sistema real, podrías tener una tabla de mapeo user -> employee
        employee_id = current_user.get("user_id")
        if not employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo determinar el ID del empleado para el usuario actual",
            )

        # Crear el caso de uso
        use_case = CreateTimeOffRequestUseCase(gateway)

        # Ejecutar la creación de la solicitud
        # Si description es None, usar valor por defecto
        description = request_data.description or "Solicitud de tiempo personal"

        result = use_case.execute(
            employee_id=employee_id,
            holiday_status_id=request_data.holiday_status_id,
            request_date_from=request_data.request_date_from,
            request_date_to=request_data.request_date_to,
            description=description,
        )

        # Devolver la respuesta exitosa
        return TimeOffRequestResponse(
            request_id=result.request_id, success=result.success, message=result.message
        )
    except ValueError as e:
        # Errores de validación → HTTP 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Errores de Odoo/negocio → HTTP 400 (datos rechazados por reglas de negocio)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/requests", response_model=List[TimeOffRequestInfoResponse])
async def get_employee_timeoff_requests(
    date_from: Optional[date] = Query(
        None, description="Fecha de inicio del filtro (YYYY-MM-DD)"
    ),
    date_to: Optional[date] = Query(
        None, description="Fecha de fin del filtro (YYYY-MM-DD)"
    ),
    gateway: TimeOffGateway = Depends(get_timeoff_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene las solicitudes de tiempo personal del empleado autenticado.

    Permite filtrar las solicitudes por rango de fechas. Si no se especifican filtros,
    retorna todas las solicitudes del empleado.

    Args:
        date_from: Fecha de inicio del filtro (opcional)
        date_to: Fecha de fin del filtro (opcional)
        gateway: Gateway para operaciones de tiempo personal
        current_user: Usuario autenticado actual

    Returns:
        List[TimeOffRequestInfoResponse]: Lista de solicitudes del empleado

    Raises:
        HTTPException: Si hay errores en la validación o consulta
    """
    try:
        # Obtener el employee_id del usuario autenticado
        employee_id = current_user.get("user_id")
        if not employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo determinar el ID del empleado para el usuario actual",
            )

        # Crear el caso de uso
        use_case = GetEmployeeTimeOffRequestsUseCase(gateway)

        # Ejecutar la consulta
        timeoff_requests = use_case.execute(
            employee_id=employee_id, date_from=date_from, date_to=date_to
        )

        # Convertir a schemas de respuesta
        return [
            TimeOffRequestInfoResponse(
                id=request.id,
                holiday_status_id=request.holiday_status_id,
                holiday_status_name=request.holiday_status_name,
                name=request.name,
                request_date_from=request.request_date_from,
                request_date_to=request.request_date_to,
                employee_id=request.employee_id,
                employee_name=request.employee_name,
                state=request.state,
                number_of_days=request.number_of_days,
            )
            for request in timeoff_requests
        ]

    except ValueError as e:
        # Errores de validación → HTTP 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Errores de Odoo/negocio → HTTP 400 (datos rechazados por reglas de negocio)
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/requests/{request_id}", response_model=TimeOffRequestResponse)
async def update_timeoff_request(
    request_id: int,
    request_data: TimeOffRequestUpdate,
    gateway: TimeOffGateway = Depends(get_timeoff_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Actualiza una solicitud de tiempo personal existente en el sistema.

    Args:
        request_id: ID de la solicitud a actualizar
        request_data: Nuevos datos para la solicitud de tiempo personal
        gateway: Gateway para operaciones de tiempo personal
        current_user: Usuario autenticado actual

    Returns:
        TimeOffRequestResponse: Resultado de la operación de actualización

    Raises:
        HTTPException: Si hay errores en la validación, permisos o actualización
    """
    try:
        # Obtener el employee_id del usuario autenticado
        employee_id = current_user.get("user_id")
        if not employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo determinar el ID del empleado para el usuario actual",
            )

        # Crear el caso de uso
        use_case = UpdateTimeOffRequestUseCase(gateway)

        # Si description es None, usar valor por defecto
        description = (
            request_data.description or "Solicitud de tiempo personal actualizada"
        )

        # Ejecutar la actualización de la solicitud
        result = use_case.execute(
            request_id=request_id,
            employee_id=employee_id,
            holiday_status_id=request_data.holiday_status_id,
            request_date_from=request_data.request_date_from,
            request_date_to=request_data.request_date_to,
            description=description,
        )

        # Devolver la respuesta exitosa
        return TimeOffRequestResponse(
            request_id=result.request_id, success=result.success, message=result.message
        )

    except ValueError as e:
        # Errores de validación → HTTP 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Errores de Odoo/negocio → HTTP 400 (datos rechazados por reglas de negocio)
        raise HTTPException(status_code=400, detail=str(e))

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
    print(last_successful_run)
    
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
            error_msg = f"Error en sincronización de nuevas solicitudes: {str(e)}"
            sync_log.errors_count += 1
            sync_log.error_message = error_msg
        
        # 2. Sincronizar actualizaciones de estado (desde la última ejecución exitosa)
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
        if total_errors == 0 and (
            (new_requests_result and new_requests_result.successfully_synced > 0) or
            (status_updates_result and status_updates_result.status_updates_count > 0)
        ):
            sync_log.mark_as_success()
            message = "Sincronización completada exitosamente"
        elif total_errors > 0 and (
            (new_requests_result and new_requests_result.successfully_synced > 0) or
            (status_updates_result and status_updates_result.status_updates_count > 0)
        ):
            sync_log.mark_as_partial_success()
            message = f"Sincronización completada con {total_errors} error(es)"
        else:
            sync_log.mark_as_error(
                sync_log.error_message or "Sincronización falló sin procesar solicitudes"
            )
            message = sync_log.error_message or "Error en la sincronización"
        
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