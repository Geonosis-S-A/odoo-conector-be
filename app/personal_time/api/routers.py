from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.personal_time.api.schemas import LeaveTypeResponse
from app.personal_time.application.use_cases.get_leave_types import GetLeaveTypesUseCase
from app.personal_time.domain.gateway import LeaveTypeGateway
from app.personal_time.infra.external.odoo_leave_type_gateway import OdooLeaveTypeGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.shared.security.dependencies import get_current_user


router = APIRouter(prefix="/personal-time", tags=["personal-time"])


def get_leave_type_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> LeaveTypeGateway:
    """Dependencia para obtener el gateway de tipos de licencias."""
    try:
        return OdooLeaveTypeGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail="Error al conectar con el gateway de tipos de licencias"
        )


@router.get("/leave-types", response_model=List[LeaveTypeResponse])
async def get_leave_types(
    gateway: LeaveTypeGateway = Depends(get_leave_type_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene todos los tipos de licencias disponibles en el sistema.

    Returns:
        List[LeaveTypeResponse]: Lista de tipos de licencias disponibles
    """
    try:
        use_case = GetLeaveTypesUseCase(gateway)
        leave_types = use_case.execute()
        
        return [
            LeaveTypeResponse(
                id=leave_type.id,
                name=leave_type.name,
            )
            for leave_type in leave_types
        ]
    except HTTPException:
        raise

