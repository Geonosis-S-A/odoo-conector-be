from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import date

from app.personal_time.api.schemas import (
    TimeOffTypeResponse,
    TimeOffRequestCreate,
    TimeOffRequestUpdate,
    TimeOffRequestResponse,
    TimeOffRequestInfoResponse,
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
