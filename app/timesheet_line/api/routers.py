from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict


from app.timesheet_line.api.schemas import (
    CargarHorasRequest,
    DetailedTimesheetLineResponse,
)
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)


router = APIRouter(prefix="/timesheet", tags=["timesheet"])


def get_timesheet_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TimesheetLineGateway:
    try:
        return OdooTimesheetLineGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al conectar con el gateway")


@router.post("/", response_model=Dict[str, int])
async def create_timesheet_line(
    request: CargarHorasRequest,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
):
    """
    Crea una nueva línea de timesheet.

    Args:
        request: Datos de la línea de timesheet a crear
        gateway: Gateway de timesheet (inyectado)

    Returns:
        Dict[str, int]: Diccionario con el ID de la línea de timesheet creada
    """
    try:
        use_case = CargarHorasUseCase(gateway)
        line = use_case.execute(request)
        return {"id": line.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al crear la línea de timesheet",
        )


@router.get("/", response_model=List[DetailedTimesheetLineResponse])
async def list_timesheet_lines(
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_id: int | None = None,
):
    """
    Lista todas las líneas de timesheet.

    Args:
        gateway: Gateway de timesheet (inyectado)

    Returns:
        List[TimesheetLine]: Lista de líneas de timesheet
    """
    try:
        timesheets = gateway.all(employee_id)
        return timesheets
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al listar las líneas de timesheet",
        )


@router.delete("/{timesheet_id}", response_model=Dict[str, str])
async def delete_timesheet_line(
    timesheet_id: int,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
):
    """
    Elimina una línea de timesheet.

    Args:
        timesheet_id: ID de la línea de timesheet a eliminar
        gateway: Gateway de timesheet (inyectado)

    Returns:
        Dict[str, str]: Mensaje de éxito
    """
    try:
        success = gateway.delete(timesheet_id)
        if not success:
            raise HTTPException(
                status_code=404, detail="Línea de timesheet no encontrada"
            )
        return {"message": "Línea de timesheet eliminada correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al eliminar la línea de timesheet",
        )
