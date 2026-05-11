from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.auth.infra.auth_service import JWTPayload
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.employee_price.infra.db.repositories import SQLModelEmployeePriceRepository
from app.users.infra.db.repositories import SQLModelUserRepository
from app.employee_price.api.schemas import (
    CreateEmployeePriceRequest,
    CreateEmployeePriceResponse,
    EmployeePriceWithUserResponse,
    TeamEmployeePriceItem,
    EmployeePriceHistoryItem,
)
from app.employee_price.application.use_cases.create_employee_price import (
    CreateEmployeePriceUseCase,
)
from app.employee_price.application.use_cases.list_team_employee_prices import (
    ListTeamEmployeePricesUseCase,
)
from app.employee_price.application.use_cases.get_employee_price_history import (
    GetEmployeePriceHistoryUseCase,
)
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.domain.repositories import EmployeeGateway
from app.shared.security.roles import user_has_role, Roles
from app.shared.security.authorization import ensure_employee_in_team

router = APIRouter(prefix="/employees-price", tags=["employees-price"])


def get_timesheet_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TimesheetLineGateway:
    """Dependencia para obtener el gateway de timesheet"""
    try:
        return OdooTimesheetLineGateway(odoo_connection)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de timesheet"
        )


def get_employee_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> EmployeeGateway:
    """Dependencia para obtener el gateway de empleados (Odoo)."""
    try:
        return OdooEmployeeGateway(odoo_connection)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de empleados"
        )


@router.get("/", response_model=list[TeamEmployeePriceItem])
async def list_team_employee_prices(
    db: Session = Depends(get_db),
    timesheet_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Lista los precios por hora de los miembros del equipo del usuario autenticado.

    Obtiene todos los miembros del equipo usando la jerarquía de Odoo y retorna
    únicamente sus registros abiertos (date_to = NULL).

    Args:
        db: Sesión de base de datos
        timesheet_gateway: Gateway para obtener información del equipo desde Odoo
        current_user: Usuario autenticado

    Returns:
        Lista de miembros del equipo con sus registros abiertos de precio
    """
    # Obtener datos del usuario autenticado
    roles: list[int] = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)
    if not is_approver:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver el listado de precios de empleados",
        )
    user_id = current_user["user_id"]

    # Inicializar repositorio
    employee_price_repository = SQLModelEmployeePriceRepository(db)
    employee_gateway = OdooEmployeeGateway(get_odoo_connection())
    # Crear y ejecutar caso de uso
    use_case = ListTeamEmployeePricesUseCase(
        employee_price_repository=employee_price_repository,
        timesheet_line_gateway=timesheet_gateway,
        employee_gateway=employee_gateway,
    )

    try:
        team_prices = use_case.execute(user_id=user_id)

        # Convertir a schema de respuesta
        team_members = [TeamEmployeePriceItem(**item) for item in team_prices]

        return team_members

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise


@router.get("/history/{employee_id}", response_model=list[EmployeePriceHistoryItem])
async def get_employee_price_history(
    employee_id: int,
    db: Session = Depends(get_db),
    timesheet_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Obtiene el historial completo de precios de un empleado específico.

    Retorna todos los registros de employee_price para el usuario,
    ordenados por fecha de más reciente a más antiguo.

    Args:
        employee_id: ID del usuario/empleado del cual obtener el historial
        db: Sesión de base de datos
        timesheet_gateway: Gateway para validar membresía de equipo
        employee_gateway: Gateway para resolver el empleado del solicitante
        current_user: Usuario autenticado

    Returns:
        Lista de registros de precio del empleado ordenados por fecha (desc)

    Raises:
        HTTPException 400: Si el employee_id es inválido
        HTTPException 403: Si el empleado no pertenece al equipo del solicitante
        HTTPException 404: Si el empleado existe en el scope pero no tiene
            registro en la BD local
    """
    roles: list[int] = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)
    if not is_approver:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver el historial de precios de un empleado",
        )

    # Scope check (VT-02, pentest 2026-04): un approver solo puede ver el
    # historial de empleados que pertenezcan a su equipo (jerarquía Odoo).
    # Se valida ANTES de tocar la BD local para evitar enumeration vía 404.
    ensure_employee_in_team(
        requester_user_id=current_user["user_id"],
        target_employee_id=employee_id,
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )

    user_repository = SQLModelUserRepository(db)
    employee_data = user_repository.get_by_id(employee_id)
    if not employee_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con employee_id {employee_id} no encontrado",
        )

    # Inicializar repositorio
    employee_price_repository = SQLModelEmployeePriceRepository(db)

    # Crear y ejecutar caso de uso
    use_case = GetEmployeePriceHistoryUseCase(
        employee_price_repository=employee_price_repository
    )

    try:
        price_history = use_case.execute(employee_id=employee_id)

        # Convertir a schema de respuesta
        history_items = [
            EmployeePriceHistoryItem.model_validate(price) for price in price_history
        ]

        return history_items

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise


@router.post("/", response_model=CreateEmployeePriceResponse)
async def create_employee_price(
    request: CreateEmployeePriceRequest,
    db: Session = Depends(get_db),
    timesheet_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Crea un nuevo registro de precio por hora para un empleado.

    Si existe un registro activo previo (con date_to vacío), automáticamente
    se cerrará ese registro estableciendo su date_to.

    Args:
        request: Datos del nuevo registro de precio de empleado
        db: Sesión de base de datos
        timesheet_gateway: Gateway para validar membresía de equipo
        employee_gateway: Gateway para resolver el empleado del solicitante
        current_user: Usuario autenticado

    Returns:
        CreateEmployeePriceResponse con el registro creado

    Raises:
        HTTPException 400: Si los datos son inválidos (costo <= 0, fechas incorrectas, etc.)
        HTTPException 403: Si el usuario no tiene permisos o el empleado
            objetivo no pertenece a su equipo
        HTTPException 404: Si el usuario no existe en la BD local
    """
    roles: list[int] = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)
    if not is_approver:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear un registro de precio de empleado",
        )

    # Scope check (VT-02, pentest 2026-04): un approver solo puede crear/editar
    # el costo de empleados de su equipo. Antes de este fix, cualquier approver
    # podía sobrescribir el costo por hora de cualquier empleado del sistema.
    ensure_employee_in_team(
        requester_user_id=current_user["user_id"],
        target_employee_id=request.employee_id,
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )

    employee_price_repository = SQLModelEmployeePriceRepository(db)
    user_repository = SQLModelUserRepository(db)

    user = user_repository.get_by_id(request.employee_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El empleado {request.employee_id} no se ha registrado en el sistema",
        )

    # Crear y ejecutar caso de uso
    use_case = CreateEmployeePriceUseCase(
        employee_price_repository=employee_price_repository
    )

    try:
        # Ejecutar creación
        created_employee_price = use_case.execute(
            employee_id=request.employee_id,
            date_from=request.date_from,
            cost_per_hour=request.cost_per_hour,
        )

        # Validar que el registro fue creado correctamente
        if created_employee_price.id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Error al crear el registro de precio de empleado",
            )

        # Convertir a response schema con datos del usuario
        employee_price_response = EmployeePriceWithUserResponse(
            id=created_employee_price.id,
            user_id=created_employee_price.user_id,
            email=user.email,
            full_name=user.full_name,
            date_from=created_employee_price.date_from,
            cost_per_hour=created_employee_price.cost_per_hour,
            date_to=created_employee_price.date_to,
        )

        return CreateEmployeePriceResponse(
            success=True,
            message="Registro de precio de empleado creado exitosamente",
            employee_price=employee_price_response,
        )

    except ValueError as e:
        # Errores de validación de negocio
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise
