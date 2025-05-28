from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Optional
from datetime import date


from app.shared.security.dependencies import get_current_user
from app.timesheet_line.api.schemas import (
    CargarHorasRequest,
    DetailedTimesheetLineResponse,
    EditTimesheetRequest,
)
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.application.use_cases.delete_timesheet import (
    DeleteTimesheetUseCase,
)
from app.timesheet_line.application.use_cases.edit_timesheet import EditTimesheetUseCase
from app.timesheet_line.application.use_cases.obtener_horas import (
    ListTimesheetLinesUseCase,
)
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.users.domain.repositories import EmployeeGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.timesheet_line.application.excepctions.exceptions import (
    InvalidHoursError,
    TimesheetNotFoundError,
    TimesheetCreationError,
    TimesheetDomainError,
    TimesheetListError,
    InvalidDateRangeError,
    InvalidEmployeeIdError,
    EmployeeNotExistsError,
)


router = APIRouter(prefix="/timesheet", tags=["timesheet"])


def get_timesheet_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TimesheetLineGateway:
    try:
        return OdooTimesheetLineGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al conectar con el gateway")


def get_employee_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> EmployeeGateway:
    try:
        return OdooEmployeeGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de empleados"
        )


@router.post("/", response_model=Dict[str, int])
async def create_timesheet_line(
    request: CargarHorasRequest,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: dict = Depends(get_current_user),
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
    except InvalidHoursError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetCreationError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al crear la línea de timesheet",
        )


@router.get("/", response_model=List[DetailedTimesheetLineResponse])
async def list_timesheet_lines(
    gateway: OdooTimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    employee_id: int = Query(..., description="ID del empleado para filtrar"),
    date_from: date = Query(..., description="Fecha de inicio del rango (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin del rango (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Lista todas las líneas de timesheet con filtros obligatorios.

    Args:
        gateway: Gateway de timesheet (inyectado)
        employee_gateway: Gateway de empleados (inyectado)
        employee_id: ID del empleado para filtrar (obligatorio)
        date_from: Fecha de inicio del rango para filtrar (obligatorio)
        date_to: Fecha de fin del rango para filtrar (obligatorio)

    Returns:
        List[DetailedTimesheetLineResponse]: Lista de líneas de timesheet
    """
    try:
        use_case = ListTimesheetLinesUseCase(gateway, employee_gateway)
        timesheets = use_case.execute(employee_id, date_from, date_to)
        return timesheets
    except InvalidEmployeeIdError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except EmployeeNotExistsError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except InvalidDateRangeError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except TimesheetListError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al listar las líneas de timesheet",
        )


@router.delete("/{timesheet_id}", response_model=Dict[str, str])
async def delete_timesheet_line(
    timesheet_id: int,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: dict = Depends(get_current_user),
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
        use_case = DeleteTimesheetUseCase(gateway)
        success = use_case.execute(timesheet_id)
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


@router.put("/{timesheet_id}")
def edit_timesheet(
    timesheet_id: int,
    req: EditTimesheetRequest,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, bool]:
    """Edita una línea de hoja de tiempo existente.

    Args:
        timesheet_id: ID de la línea de hoja de tiempo a editar
        req: Datos de la línea de hoja de tiempo
        gateway: Gateway para interactuar con Odoo

    Returns:
        Dict[str, bool]: Resultado de la operación

    Raises:
        HTTPException: Si hay un error al editar la línea
    """
    try:
        # Asegurar que el ID en la URL coincide con el ID en el body
        if timesheet_id != req.id:
            raise HTTPException(
                status_code=400,
                detail="El ID en la URL no coincide con el ID en el body",
            )

        # Verificar que la línea existe antes de intentar editarla
        try:
            gateway.get_by_id(timesheet_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="No se encontró la línea de timesheet",
            )

        use_case = EditTimesheetUseCase(gateway)
        success = use_case.execute(req)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="No se pudo actualizar la línea de timesheet",
            )

        return {"success": True}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al editar la línea de hoja de tiempo: {str(e)}",
        )
