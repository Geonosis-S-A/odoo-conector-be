from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.personal_time.api.schemas import TimeOffTypeResponse, TimeOffRequestCreate, TimeOffRequestResponse
from app.personal_time.application.use_cases.get_timeoff_types import GetTimeOffTypesUseCase
from app.personal_time.application.use_cases.create_timeoff_request import CreateTimeOffRequestUseCase
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway
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
            detail="Error al conectar con el gateway de tipos de licencias"
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
    try:
        use_case = GetTimeOffTypesUseCase(gateway)
        timeoff_types = use_case.execute()
        
        return [
            TimeOffTypeResponse(
                id=timeoff_type.id,
                name=timeoff_type.name,
            )
            for timeoff_type in timeoff_types
        ]
    except HTTPException:
        raise


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
                detail="No se pudo determinar el ID del empleado para el usuario actual"
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
            description=description
        )

        # Devolver la respuesta exitosa
        return TimeOffRequestResponse(
            request_id=result.request_id,
            success=result.success,
            message=result.message
        )

    except HTTPException:
        raise

