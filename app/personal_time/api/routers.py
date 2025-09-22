from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.personal_time.api.schemas import TimeOffTypeResponse
from app.personal_time.application.use_cases.get_timeoff_types import GetTimeOffTypesUseCase
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.shared.security.dependencies import get_current_user


router = APIRouter(prefix="/personal-time", tags=["personal-time"])


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


@router.get("/timeoff-types", response_model=List[TimeOffTypeResponse])
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

