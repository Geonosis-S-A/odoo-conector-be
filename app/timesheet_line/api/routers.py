from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict
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
    TimesheetIdMismatchError,
    TimesheetEditError,
    TimesheetDeleteError,
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


@router.post("/", response_model=list[DetailedTimesheetLineResponse])
async def create_timesheet_line(
    request: list[CargarHorasRequest],
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Crea nuevas líneas de timesheet.

    Args:
        request: Lista de datos de las líneas de timesheet a crear
        gateway: Gateway de timesheet (inyectado)

    Returns:
        list[DetailedTimesheetLineResponse]: Lista de líneas de timesheet creadas con detalles
    """
    try:
        use_case = CargarHorasUseCase(gateway)
        lines = use_case.execute(request)
        return lines
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


@router.delete("/", response_model=Dict[str, str])
async def delete_timesheet_line(
    request: list[int],
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Elimina múltiples líneas de timesheet.

    Args:
        request: Lista de IDs de las líneas de timesheet a eliminar
        gateway: Gateway de timesheet (inyectado)

    Returns:
        Dict[str, str]: Mensaje de éxito
    """
    try:
        use_case = DeleteTimesheetUseCase(gateway)
        success = use_case.execute(request)
        return {"message": "Líneas de timesheet eliminadas correctamente"}
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetDeleteError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al eliminar las líneas de timesheet",
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
            raise TimesheetIdMismatchError(timesheet_id, req.id)

        use_case = EditTimesheetUseCase(gateway)
        success = use_case.execute(req)
        return {"success": success}
    except TimesheetIdMismatchError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InvalidHoursError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetEditError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al editar la línea de timesheet",
        )
