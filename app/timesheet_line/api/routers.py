from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict

from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineRepository
from app.timesheet_line.infra.external.odoo.get_odoo import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_repository import (
    OdooTimesheetLineRepository,
)


router = APIRouter(prefix="/timesheet", tags=["timesheet"])


def get_timesheet_repository() -> TimesheetLineRepository:
    try:
        odoo_client = get_odoo_connection()
        return OdooTimesheetLineRepository(odoo_client)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el repositorio"
        )


@router.post("/", response_model=Dict[str, int])
async def create_timesheet_line(
    request: CargarHorasRequest,
    repository: TimesheetLineRepository = Depends(get_timesheet_repository),
):
    """
    Crea una nueva línea de timesheet.

    Args:
        request: Datos de la línea de timesheet a crear
        repository: Repositorio de timesheet (inyectado)

    Returns:
        Dict[str, int]: Diccionario con el ID de la línea de timesheet creada
    """
    try:
        use_case = CargarHorasUseCase(repository)
        timesheet_id = use_case.execute(request)
        return {"id": timesheet_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al crear la línea de timesheet",
        )


@router.get("/", response_model=List[TimesheetLine])
async def list_timesheet_lines(
    repository: TimesheetLineRepository = Depends(get_timesheet_repository),
):
    """
    Lista todas las líneas de timesheet.

    Args:
        repository: Repositorio de timesheet (inyectado)

    Returns:
        List[TimesheetLine]: Lista de líneas de timesheet
    """
    try:
        timesheets = repository.all()
        return [
            TimesheetLine(
                id=ts.id,
                name=ts.name,
                employee_id=ts.employee_id,
                project_id=ts.project_id,
                hours=ts.hours,
                date=ts.date,
                task_id=ts.task_id,
            )
            for ts in timesheets
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al listar las líneas de timesheet",
        )


@router.delete("/{timesheet_id}", response_model=Dict[str, str])
async def delete_timesheet_line(
    timesheet_id: int,
    repository: TimesheetLineRepository = Depends(get_timesheet_repository),
):
    """
    Elimina una línea de timesheet.

    Args:
        timesheet_id: ID de la línea de timesheet a eliminar
        repository: Repositorio de timesheet (inyectado)

    Returns:
        Dict[str, str]: Mensaje de éxito
    """
    try:
        success = repository.delete(timesheet_id)
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
