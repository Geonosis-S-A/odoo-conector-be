from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Dict
from datetime import date
import xmlrpc.client

from sqlmodel import Session

from app.email.api.dependencies import get_common_email_service
from app.email.api.schemas import ApprovedMailRequest, ReviewMailRequest
from app.email.infra.email_service import CommonResendEmailService
from app.email.domain.email_types import TimesheetEmailType
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles, user_has_role
from app.timesheet_line.api.schemas import (
    CargarHorasRequest,
    DetailedTimesheetLineResponse,
    EditTimesheetRequest,
    DeleteTimesheetRequest,
    ValidateTimesheetRequest,
    PaginatedTimesheetLinesResponse,
)
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.application.use_cases.delete_timesheet import (
    DeleteTimesheetUseCase,
)
from app.timesheet_line.application.use_cases.edit_timesheet import EditTimesheetUseCase
from app.timesheet_line.application.use_cases.obtener_horas import (
    ListTimesheetLinesUseCase,
)
from app.timesheet_line.application.use_cases.validar_timesheet import (
    ValidateTimesheetUseCase,
)
from app.timesheet_line.application.use_cases.review_timesheets import (
    ReviewTimesheetsUseCase,
)
from app.timesheet_line.domain.models import CreateTimesheetLineNotification
from app.timesheet_line.domain.repositories import (
    TimesheetLineGateway,
    TimesheetLineNotificationRepository,
)
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.timesheet_line.infra.db.repositories import (
    SQLModelTimesheetLineNotificationRepository,
)
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.task.domain.gateway import TaskGateway
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
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
    OdooValidationError,
    OdooConnectionError,
    TimesheetValidateError,
    ApproverNotFoundError,
    TimesheetReviewError,
)
from app.shared.security.authorization import (
    get_team_scope,
    ensure_owns_timesheets,
    ensure_employee_in_team,
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


def get_task_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TaskGateway:
    try:
        return OdooTaskGateway(odoo_connection)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de tareas"
        )


def get_notification_repository(
    db: Session = Depends(get_db),
) -> TimesheetLineNotificationRepository:
    return SQLModelTimesheetLineNotificationRepository(db)


# VT-08 / VT-15 (pentest 2026-04): paginación obligatoria y rechazo de
# `employee_id` duplicado en query (HTTP Parameter Pollution).
VT08_MAX_PAGE_SIZE = 100


def single_employee_id_query(request: Request) -> int | None:
    """Un solo valor para `employee_id` en la query string."""
    raw = request.query_params.getlist("employee_id")
    if len(raw) > 1:
        raise HTTPException(
            status_code=400,
            detail="Parámetro employee_id duplicado",
        )
    if not raw or raw[0] == "":
        return None
    try:
        v = int(raw[0])
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="employee_id debe ser un entero",
        )
    if v <= 0:
        raise HTTPException(status_code=400, detail="employee_id inválido")
    return v


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
    except xmlrpc.client.Fault as fault_error:
        # Error específico de Odoo (validaciones, restricciones, etc.)
        raise HTTPException(
            status_code=422,
            detail=f"Error de validación de Odoo: {fault_error.faultString}",
        )
    except xmlrpc.client.ProtocolError as protocol_error:
        # Error de protocolo HTTP/HTTPS
        raise HTTPException(
            status_code=503,
            detail=f"Error de conexión con Odoo: {protocol_error.errcode} - {protocol_error.errmsg}",
        )
    except OdooValidationError as e:
        # Devolver exactamente el error que retorna Odoo
        raise HTTPException(
            status_code=422,
            detail=f"Error de validación de Odoo: {e.odoo_error_message}",
        )
    except OdooConnectionError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetCreationError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/", response_model=PaginatedTimesheetLinesResponse)
async def list_timesheet_lines(
    gateway: OdooTimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    employee_id: int | None = Depends(single_employee_id_query),
    date_from: date | None = Query(
        None, description="Fecha de inicio del rango (YYYY-MM-DD)"
    ),
    date_to: date | None = Query(
        None, description="Fecha de fin del rango (YYYY-MM-DD)"
    ),
    project_id: int | None = Query(None, description="ID del proyecto para filtrar"),
    validated: bool | None = Query(
        None, description="Filtrar por estado de validación"
    ),
    current_user: dict = Depends(get_current_user),
    notification_repository: TimesheetLineNotificationRepository = Depends(
        get_notification_repository
    ),
    task_gateway: TaskGateway = Depends(get_task_gateway),
    team: bool | None = Query(None, description="Filtrar por equipo (subordinados)"),
    page: int = Query(1, ge=1, description="Página (base 1)"),
    page_size: int = Query(
        100,
        ge=1,
        le=VT08_MAX_PAGE_SIZE,
        description=f"Tamaño de página (máximo {VT08_MAX_PAGE_SIZE})",
    ),
):
    """
    Lista líneas de timesheet con **paginación obligatoria** (máx. 100 por página).

    VT-08: un usuario con rol approver ya no puede obtener un volcado global de
    toda la empresa omitiendo filtros; sin `employee_id` ni `team`, solo ve
    sus propios registros. Un approver que pasa `employee_id` ajeno debe tener
    scope de equipo (misma regla que VT-04).

    VT-15: `employee_id` duplicado en la query se rechaza con HTTP 400.
    """
    roles: list[int] = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)
    requester_id = current_user["user_id"]

    effective_employee_id = employee_id
    if is_approver:
        if employee_id is not None:
            ensure_employee_in_team(
                requester_user_id=requester_id,
                target_employee_id=employee_id,
                employee_gateway=employee_gateway,
                timesheet_gateway=gateway,
            )
        elif not team:
            # Antes: sin filtro de empleado → Odoo devolvía miles de registros.
            effective_employee_id = requester_id
    else:
        if employee_id is None or employee_id != requester_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver esta información",
            )

    try:
        use_case = ListTimesheetLinesUseCase(
            gateway,
            employee_gateway,
            notification_repository,
            task_gateway,
        )
        result = use_case.execute(
            effective_employee_id,
            date_from,
            date_to,
            project_id,
            validated,
            team,
            requester_id,
            page=page,
            page_size=page_size,
        )
        return PaginatedTimesheetLinesResponse(
            items=result.items,
            total=result.total,
            page=page,
            page_size=page_size,
        )
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


@router.delete("/", response_model=Dict[str, str])
async def delete_timesheet_line(
    request: DeleteTimesheetRequest,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Elimina múltiples líneas de timesheet.

    Args:
        request: Objeto con lista de IDs de las líneas de timesheet a eliminar
        gateway: Gateway de timesheet (inyectado)
        employee_gateway: Gateway de empleados (para resolver scope)
        current_user: Usuario autenticado

    Returns:
        Dict[str, str]: Mensaje de éxito

    Raises:
        HTTPException 403: Si alguno de los timesheets no pertenece al
            solicitante ni a su equipo (IDOR check de VT-04, pentest 2026-04).
    """
    # Ownership check (VT-04 + bonus, pentest 2026-04):
    # Antes de este fix, cualquier usuario autenticado podía borrar timesheets
    # de cualquier empleado. Ahora exigimos que el dueño sea el propio
    # solicitante o esté bajo su jerarquía en Odoo, atómicamente para todos
    # los IDs del lote (todo o nada).
    existing = gateway.get_by_ids(request.ids)
    if not existing or len(existing) != len(request.ids):
        raise HTTPException(
            status_code=404,
            detail="Uno o más timesheets no fueron encontrados",
        )
    ensure_owns_timesheets(
        requester_user_id=current_user["user_id"],
        target_employee_ids=[ts.employee_id for ts in existing],
        employee_gateway=employee_gateway,
        timesheet_gateway=gateway,
    )

    try:
        use_case = DeleteTimesheetUseCase(gateway)
        use_case.execute(request.ids)
        return {"message": "Líneas de timesheet eliminadas correctamente"}
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetDeleteError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)


@router.put("/{timesheet_id}")
def edit_timesheet(
    timesheet_id: int,
    req: EditTimesheetRequest,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, bool]:
    """Edita una línea de hoja de tiempo existente.

    Args:
        timesheet_id: ID de la línea de hoja de tiempo a editar
        req: Datos de la línea de hoja de tiempo
        gateway: Gateway para interactuar con Odoo
        employee_gateway: Gateway de empleados (para resolver scope)
        current_user: Usuario autenticado

    Returns:
        Dict[str, bool]: Resultado de la operación

    Raises:
        HTTPException 403: Si el timesheet no pertenece al solicitante ni a su
            equipo (IDOR check de VT-04), o si el body intenta cambiar
            `employee_id` (transferencia de timesheet entre empleados).
        HTTPException: Si hay un error al editar la línea
    """
    roles: list[int] = current_user["roles"]
    is_admin = user_has_role(roles, Roles.approver)

    if req.validated and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para editar las líneas de timesheet si ya fueron validadas",
        )

    # Asegurar que el ID en la URL coincide con el ID en el body (validación
    # previa al ownership check para evitar mensajes confusos).
    if timesheet_id != req.id:
        raise HTTPException(
            status_code=400,
            detail=TimesheetIdMismatchError(timesheet_id, req.id).message,
        )

    # Ownership check (VT-04, pentest 2026-04):
    # 1) El timesheet debe existir en Odoo.
    # 2) Su dueño actual debe ser el solicitante, o estar en su equipo.
    # 3) El body NO puede cambiar `employee_id` (eso sería transferir el
    #    registro a un tercero, que también es un IDOR/integridad).
    existing_timesheet = gateway.get_by_id(req.id)
    if existing_timesheet is None:
        raise HTTPException(
            status_code=404,
            detail=TimesheetNotFoundError([req.id]).message,
        )

    scope = get_team_scope(
        requester_user_id=current_user["user_id"],
        employee_gateway=employee_gateway,
        timesheet_gateway=gateway,
    )
    if not scope.contains(existing_timesheet.employee_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para editar este timesheet",
        )
    if req.employee_id != existing_timesheet.employee_id:
        raise HTTPException(
            status_code=403,
            detail="No se puede cambiar el empleado dueño de un timesheet existente",
        )

    try:
        use_case = EditTimesheetUseCase(gateway)
        success = use_case.execute(req)
        return {"success": success}
    except InvalidHoursError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetEditError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)

@router.post("/validate", response_model=Dict[str, bool])
async def validate_timesheet_lines(
    request: ApprovedMailRequest,
    gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    email_service: CommonResendEmailService = Depends(get_common_email_service),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    notification_repository: TimesheetLineNotificationRepository = Depends(
        get_notification_repository
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Valida múltiples líneas de timesheet (marca validated=True).

    Args:
        request: Objeto con lista de IDs de las líneas de timesheet a validar
        gateway: Gateway de timesheet (inyectado)

    Returns:
        Dict[str, bool]: Resultado de la validación

    Raises:
        HTTPException 403: Si el solicitante no es approver, si intenta usar
            un `approver_mail` distinto al propio (spoofing) o si alguno de
            los timesheets no pertenece a su equipo (VT-14, pentest 2026-04).
    """
    roles: list[int] = current_user["roles"]
    is_admin = user_has_role(roles, Roles.approver)
    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para validar las líneas de timesheet",
        )

    # VT-14 (pentest 2026-04) — anti-spoofing del approver:
    # antes, el `approver_mail` se aceptaba tal cual desde el body, lo que
    # permitía a un approver enviar mails al empleado diciendo "aprobado por
    # <otro_aprobador>". Lo forzamos al email del solicitante autenticado.
    if request.approver_mail != current_user["user_email"]:
        raise HTTPException(
            status_code=403,
            detail="No podés validar timesheets en nombre de otro aprobador",
        )

    # VT-14 — scope check sobre el lote:
    # un approver solo puede validar timesheets de empleados que estén bajo
    # su jerarquía en Odoo. Atómico: si cualquier ID del lote queda fuera de
    # scope, no se valida ninguno.
    existing = gateway.get_by_ids(request.timesheetline_ids)
    if not existing or len(existing) != len(request.timesheetline_ids):
        raise HTTPException(
            status_code=404,
            detail="Uno o más timesheets no fueron encontrados",
        )
    ensure_owns_timesheets(
        requester_user_id=current_user["user_id"],
        target_employee_ids=[ts.employee_id for ts in existing],
        employee_gateway=employee_gateway,
        timesheet_gateway=gateway,
    )

    try:
        use_case = ValidateTimesheetUseCase(gateway, email_service, employee_gateway, notification_repository)
        success = await use_case.execute(request.timesheetline_ids, request.approver_mail)
        return {"success": success}
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetValidateError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/review", response_model=Dict[str, bool])
async def review_mail(
    request: ReviewMailRequest,
    email_service: CommonResendEmailService = Depends(get_common_email_service),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    timesheet_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: dict = Depends(get_current_user),
    notification_repository: TimesheetLineNotificationRepository = Depends(
        get_notification_repository
    ),
):
    """
    Envía correos de revisión o eliminación a los empleados sobre sus timesheets.

    Args:
        request: Objeto con lista de IDs de timesheets, email del aprobador, mensaje opcional y tipo de email
        email_service: Servicio de email (inyectado)
        employee_gateway: Gateway de empleados (inyectado)
        timesheet_gateway: Gateway de timesheet (inyectado)
        notification_repository: Repositorio de notificaciones (inyectado)

    Returns:
        Dict[str, bool]: Resultado del envío
    """
    roles: list[int] = current_user["roles"]
    is_admin = user_has_role(roles, Roles.approver)
    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para enviar correos de revisión",
        )

    # VT-14 (pentest 2026-04) — mismo patrón que /validate:
    # 1) `approver_mail` se fuerza al email del solicitante (anti-spoofing).
    # 2) Los timesheets del lote deben pertenecer a su equipo (scope check).
    if request.approver_mail != current_user["user_email"]:
        raise HTTPException(
            status_code=403,
            detail="No podés enviar correos de revisión en nombre de otro aprobador",
        )
    existing = timesheet_gateway.get_by_ids(request.timesheetline_ids)
    if not existing or len(existing) != len(request.timesheetline_ids):
        raise HTTPException(
            status_code=404,
            detail="Uno o más timesheets no fueron encontrados",
        )
    ensure_owns_timesheets(
        requester_user_id=current_user["user_id"],
        target_employee_ids=[ts.employee_id for ts in existing],
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )

    try:
        use_case = ReviewTimesheetsUseCase(
            employee_gateway, timesheet_gateway, email_service, notification_repository
        )
        # Obtener el tipo de email del request (por defecto REVIEW)
        email_type = request.email_type or TimesheetEmailType.REVIEW
        success = await use_case.execute(
            request.timesheetline_ids, 
            request.approver_mail, 
            request.body,
            email_type
        )
        return {"success": success}
    except ApproverNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TimesheetReviewError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except TimesheetDomainError as e:
        # Captura cualquier otra excepción del dominio
        raise HTTPException(status_code=400, detail=e.message)
