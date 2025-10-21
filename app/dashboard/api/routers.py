from datetime import date
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import StreamingResponse

from app.auth.infra.auth_service import JWTPayload
from app.dashboard.api.schemas import (
    DashboardSummaryResponse,
    DashboardSummaryMetaResponse,
    DashboardSummaryKPIsResponse,
    DashboardSummaryTotalsResponse,
    KPIResponse,
    ProjectTotalResponse,
    TaskTotalResponse,
    EmployeeTotalResponse,
    DashboardSummaryResponseByEmployee,
    DashboardSummaryMetaResponseByEmployee,
    HierarchicalSummaryResponse,
    HierarchicalItemResponse,
    TaskDetailResponse,
    SimpleTimesheetLineResponse,
)
from app.dashboard.application.use_cases.export_timesheets import (
    ExportTimesheetsByTeamUseCase,
)
from app.dashboard.application.use_cases.get_dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from app.dashboard.application.use_cases.get_dashboard_summary_by_employee import (
    GetDashboardSummaryByEmployeeUseCase,
)
from app.dashboard.application.use_cases.get_task_detail import (
    GetTaskDetailUseCase,
)
from app.dashboard.domain.repositories import DashboardDataService
from app.dashboard.infra.dashboard_service import OdooDashboardDataService
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import user_has_role, Roles
from app.users.domain.repositories import EmployeeGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.task.domain.gateway import TaskGateway
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.timesheet_line.infra.db.repositories import (
    SQLModelTimesheetLineNotificationRepository,
)
from app.timesheet_line.domain.repositories import TimesheetLineNotificationRepository
from app.employee_price.domain.repositories import EmployeePriceRepository
from app.employee_price.infra.db.repositories import SQLModelEmployeePriceRepository
from app.shared.infra.db.session import get_db, Session
import pandas as pd

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_employee_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> EmployeeGateway:
    """Dependencia para obtener el gateway de empleados."""
    try:
        return OdooEmployeeGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de empleados"
        )


def get_timesheet_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TimesheetLineGateway:
    try:
        return OdooTimesheetLineGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al conectar con el gateway")


def get_task_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TaskGateway:
    """Dependencia para obtener el gateway de tareas."""
    try:
        return OdooTaskGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de tareas"
        )


def get_dashboard_data_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    task_gateway: TaskGateway = Depends(get_task_gateway),
    timesheet_line_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
) -> DashboardDataService:
    """Dependencia para obtener el gateway de datos de dashboard."""
    try:
        return OdooDashboardDataService(
            odoo_connection, employee_gateway, task_gateway, timesheet_line_gateway
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de dashboard"
        )


def get_notification_repository(
    db: Session = Depends(get_db),
) -> TimesheetLineNotificationRepository:
    return SQLModelTimesheetLineNotificationRepository(db)


def get_employee_price_repository(
    db: Session = Depends(get_db),
) -> EmployeePriceRepository:
    """Dependencia para obtener el repositorio de precios de empleados."""
    return SQLModelEmployeePriceRepository(db)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    date_from: date = Query(..., description="Fecha de inicio del rango (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin del rango (YYYY-MM-DD)"),
    dashboard_gateway: DashboardDataService = Depends(get_dashboard_data_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    task_gateway: TaskGateway = Depends(get_task_gateway),
    timesheet_line_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_price_repository: EmployeePriceRepository = Depends(
        get_employee_price_repository
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene el resumen del dashboard para el equipo del usuario en un período específico.

    Args:
        date_from: Fecha de inicio del período (YYYY-MM-DD)
        date_to: Fecha de fin del período (YYYY-MM-DD)
        dashboard_gateway: Gateway de datos de dashboard (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        DashboardSummaryResponse: Resumen completo con KPIs y totales
    """

    roles: list[int] = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)
    if not is_approver:
        raise HTTPException(
            status_code=403, detail="No tienes permisos para ver el dashboard"
        )
    try:
        # Validar que date_from no sea posterior a date_to
        if date_from > date_to:
            raise HTTPException(
                status_code=400,
                detail="La fecha de inicio no puede ser posterior a la fecha de fin",
            )

        # Obtener user_id del usuario autenticado
        requester_employee_id = current_user["user_id"]
        user_id = employee_gateway.get_user_id_by_employee_id(requester_employee_id)
        if not user_id:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Crear y ejecutar caso de uso
        use_case = GetDashboardSummaryUseCase(
            dashboard_gateway,
            employee_gateway,
            task_gateway,
            timesheet_line_gateway,
            employee_price_repository,
        )
        dashboard_summary = use_case.execute(
            user_id, requester_employee_id, date_from, date_to
        )
        # Transformar modelo de dominio a esquema de respuesta
        response = _transform_to_response_schema(dashboard_summary)

        return response

    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise


@router.get("/summary/detail", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: Optional[int] = Query(None, description="ID de la tarea para filtrar"),
    project_id: Optional[int] = Query(
        None, description="ID del proyecto para filtrar (cuando no hay tarea)"
    ),
    date_from: date = Query(..., description="Fecha de inicio del rango (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin del rango (YYYY-MM-DD)"),
    dashboard_gateway: DashboardDataService = Depends(get_dashboard_data_gateway),
    timesheet_line_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: dict = Depends(get_current_user),
    notification_repository: TimesheetLineNotificationRepository = Depends(
        get_notification_repository
    ),
    employee_id: int | None = Query(None, description="ID del empleado para filtrar"),
):
    """
    Obtiene el detalle de empleados que cargaron horas en una tarea específica o proyecto en un período.

    Args:
        task_id: ID de la tarea a consultar (opcional)
        project_id: ID del proyecto a consultar (opcional, usado cuando task_id es None)
        date_from: Fecha de inicio del período (YYYY-MM-DD)
        date_to: Fecha de fin del período (YYYY-MM-DD)
        dashboard_gateway: Gateway de datos de dashboard (inyectado)
        timesheet_line_gateway: Gateway de líneas de timesheet (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        TaskDetailResponse: Detalle con líneas de timesheet y estadísticas
    """

    # Validar permisos
    roles: list[int] = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)

    # Si no es approver, solo puede ver información general o su propia información

    if employee_id:
        if (
            (employee_id is not None and current_user["user_id"] != employee_id)
            or (employee_id is None)
        ) and (not is_approver):
            raise HTTPException(
                status_code=403, detail="No tienes permisos para ver esta información"
            )
    else:
        if not is_approver:
            raise HTTPException(
                status_code=403, detail="No tienes permisos para ver esta información"
            )

    try:
        # Validar parámetros de entrada
        if not task_id and not project_id:
            raise HTTPException(
                status_code=400, detail="Debe proporcionar task_id o project_id"
            )

        if date_from > date_to:
            raise HTTPException(
                status_code=400,
                detail="La fecha de inicio no puede ser posterior a la fecha de fin",
            )

        # Crear y ejecutar caso de uso
        use_case = GetTaskDetailUseCase(
            dashboard_gateway,
            timesheet_line_gateway,
            employee_gateway,
            notification_repository,
        )
        task_detail = use_case.execute(
            task_id, project_id, date_from, date_to, employee_id
        )

        # Transformar líneas de timesheet al schema correcto
        timesheet_lines = [
            SimpleTimesheetLineResponse(**line)
            for line in task_detail["timesheet_lines"]
        ]

        # Crear respuesta
        response = TaskDetailResponse(
            task_id=task_detail["task_id"],
            project_id=task_detail["project_id"],
            timesheet_lines=timesheet_lines,
        )

        return response

    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise


@router.get("/summary/{employee_id}", response_model=DashboardSummaryResponseByEmployee)
async def get_dashboard_summary_by_employee(
    employee_id: int = Path(..., description="ID del empleado para filtrar"),
    date_from: date = Query(..., description="Fecha de inicio del rango (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin del rango (YYYY-MM-DD)"),
    dashboard_gateway: DashboardDataService = Depends(get_dashboard_data_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    task_gateway: TaskGateway = Depends(get_task_gateway),
    timesheet_line_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene el resumen del dashboard para el equipo del usuario en un período específico.

    Args:
        date_from: Fecha de inicio del período (YYYY-MM-DD)
        date_to: Fecha de fin del período (YYYY-MM-DD)
        dashboard_gateway: Gateway de datos de dashboard (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        DashboardSummaryResponse: Resumen completo con KPIs y totales
    """

    roles: list[int] = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)
    if (
        (employee_id is not None and current_user["user_id"] != employee_id)
        or (employee_id is None)
    ) and (not is_approver):
        raise HTTPException(
            status_code=403, detail="No tienes permisos para ver esta información"
        )
    try:
        # Validar que date_from no sea posterior a date_to
        if date_from > date_to:
            raise HTTPException(
                status_code=400,
                detail="La fecha de inicio no puede ser posterior a la fecha de fin",
            )

        # Crear y ejecutar caso de uso
        use_case = GetDashboardSummaryByEmployeeUseCase(
            dashboard_gateway, employee_gateway, task_gateway, timesheet_line_gateway
        )
        dashboard_summary = use_case.execute(employee_id, date_from, date_to)

        # Transformar modelo de dominio a esquema de respuesta
        response = _transform_to_response_schema_by_employee(dashboard_summary)

        return response

    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise


@router.get("/export-timesheets")
async def export_timesheets(
    date_from: date = Query(..., description="Fecha de inicio del rango (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin del rango (YYYY-MM-DD)"),
    dolar_value: float = Query(0, description="Valor del dólar"),
    timesheet_line_gateway: TimesheetLineGateway = Depends(get_timesheet_gateway),
    current_user: JWTPayload = Depends(get_current_user),
    task_gateway: TaskGateway = Depends(get_task_gateway),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    employee_price_repository: EmployeePriceRepository = Depends(
        get_employee_price_repository
    ),
):
    roles = current_user["roles"]
    is_approver = user_has_role(roles, Roles.approver)
    if not is_approver:
        raise HTTPException(
            status_code=403, detail="No tienes permisos para exportar timesheets"
        )

    use_case = ExportTimesheetsByTeamUseCase(
        timesheet_line_gateway,
        employee_gateway,
        task_gateway,
        current_user["user_id"],
        employee_price_repository,
        dolar_value=dolar_value,
    )
    timesheet_lines_df = use_case.execute(date_from, date_to)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        timesheet_lines_df.to_excel(writer, index=False, sheet_name="Horas")

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=horas.xlsx"},
    )


def _transform_to_response_schema(dashboard_summary) -> DashboardSummaryResponse:
    """Transforma el modelo de dominio al esquema de respuesta de la API."""

    # Transformar KPIs
    total_cost_response = None
    if (
        "total_cost" in dashboard_summary.summary
        and dashboard_summary.summary["total_cost"]
    ):
        total_cost_response = KPIResponse(
            total=dashboard_summary.summary["total_cost"].total,
            average_per_user=dashboard_summary.summary["total_cost"].average_per_user,
            unit=dashboard_summary.summary["total_cost"].unit,
        )

    summary_response = DashboardSummaryKPIsResponse(
        hours_selected_period=KPIResponse(
            total=dashboard_summary.summary["hours_selected_period"].total,
            average_per_user=dashboard_summary.summary[
                "hours_selected_period"
            ].average_per_user,
            unit=dashboard_summary.summary["hours_selected_period"].unit,
        ),
        entries_selected_period=KPIResponse(
            total=dashboard_summary.summary["entries_selected_period"].total,
            average_per_user=dashboard_summary.summary[
                "entries_selected_period"
            ].average_per_user,
            unit=dashboard_summary.summary["entries_selected_period"].unit,
        ),
        daily_average_hours=KPIResponse(
            total=dashboard_summary.summary["daily_average_hours"].total,
            average_per_user=dashboard_summary.summary[
                "daily_average_hours"
            ].average_per_user,
            unit=dashboard_summary.summary["daily_average_hours"].unit,
        ),
        total_cost=total_cost_response,
    )

    # Transformar totales
    totals_response = DashboardSummaryTotalsResponse(
        by_project=[
            ProjectTotalResponse(
                project_id=project.project_id,
                project_name=project.project_name,
                hours=project.hours,
            )
            for project in dashboard_summary.totals["by_project"]
        ],
        by_task=[
            TaskTotalResponse(
                task_id=task.task_id,
                task_name=task.task_name,
                hours=task.hours,
                project_id=task.project_id,
            )
            for task in dashboard_summary.totals["by_task"]
        ],
        by_employee=[
            EmployeeTotalResponse(
                user_id=employee.user_id,
                employee_name=employee.employee_name,
                hours=employee.hours,
                total_cost=employee.total_cost,
            )
            for employee in dashboard_summary.totals["by_employee"]
        ],
    )

    # Transformar estructura jerárquica si existe
    hierarchical_summary_response = None
    if dashboard_summary.hierarchical_summary:
        hierarchical_summary_response = _transform_hierarchical_summary(
            dashboard_summary.hierarchical_summary
        )

    # Transformar employees_without_price si existe
    employees_without_price_response = None
    if dashboard_summary.employees_without_price:
        from app.dashboard.api.schemas import EmployeeWithoutPriceResponse

        employees_without_price_response = [
            EmployeeWithoutPriceResponse(
                user_id=emp.user_id,
                employee_name=emp.employee_name,
            )
            for emp in dashboard_summary.employees_without_price
        ]

    # Crear respuesta completa
    return DashboardSummaryResponse(
        meta=DashboardSummaryMetaResponse(
            users_count=dashboard_summary.meta["users_count"]
        ),
        summary=summary_response,
        totals=totals_response,
        hierarchical_summary=hierarchical_summary_response,
        employees_without_price=employees_without_price_response,
    )


def _transform_hierarchical_summary(
    hierarchical_summary,
) -> HierarchicalSummaryResponse:
    """Transforma la estructura jerárquica del dominio al schema de respuesta."""
    return HierarchicalSummaryResponse(
        total_hours=hierarchical_summary.total_hours,
        total_cost=hierarchical_summary.total_cost,
        data=[_transform_hierarchical_item(item) for item in hierarchical_summary.data],
    )


def _transform_hierarchical_item(item) -> HierarchicalItemResponse:
    """Transforma un item jerárquico del dominio al schema de respuesta."""
    # Para nodos artificiales, no incluir el campo 'data' (siempre están vacíos)
    # Para nodos no artificiales, incluir 'data' solo si tienen hijos
    data_field = None
    if not item.is_artificial and item.data:
        data_field = [_transform_hierarchical_item(child) for child in item.data]

    return HierarchicalItemResponse(
        type=item.type,
        id=item.id,
        name=item.name,
        total_hours=item.total_hours,
        total_cost=item.total_cost,
        data=data_field,
        is_artificial=item.is_artificial,
    )


def _transform_to_response_schema_by_employee(
    dashboard_summary,
) -> DashboardSummaryResponseByEmployee:
    """Transforma el modelo de dominio al esquema de respuesta de la API."""

    # Transformar KPIs
    summary_response = DashboardSummaryKPIsResponse(
        hours_selected_period=KPIResponse(
            total=dashboard_summary.summary["hours_selected_period"].total,
            average_per_user=dashboard_summary.summary[
                "hours_selected_period"
            ].average_per_user,
            unit=dashboard_summary.summary["hours_selected_period"].unit,
        ),
        entries_selected_period=KPIResponse(
            total=dashboard_summary.summary["entries_selected_period"].total,
            average_per_user=dashboard_summary.summary[
                "entries_selected_period"
            ].average_per_user,
            unit=dashboard_summary.summary["entries_selected_period"].unit,
        ),
        daily_average_hours=KPIResponse(
            total=dashboard_summary.summary["daily_average_hours"].total,
            average_per_user=dashboard_summary.summary[
                "daily_average_hours"
            ].average_per_user,
            unit=dashboard_summary.summary["daily_average_hours"].unit,
        ),
    )

    # Transformar totales
    totals_response = DashboardSummaryTotalsResponse(
        by_project=[
            ProjectTotalResponse(
                project_id=project.project_id,
                project_name=project.project_name,
                hours=project.hours,
            )
            for project in dashboard_summary.totals["by_project"]
        ],
        by_task=[
            TaskTotalResponse(
                task_id=task.task_id,
                task_name=task.task_name,
                hours=task.hours,
                project_id=task.project_id,
            )
            for task in dashboard_summary.totals["by_task"]
        ],
        by_employee=[
            EmployeeTotalResponse(
                user_id=employee.user_id,
                employee_name=employee.employee_name,
                hours=employee.hours,
                total_cost=employee.total_cost,
            )
            for employee in dashboard_summary.totals["by_employee"]
        ],
    )

    # Transformar estructura jerárquica si existe
    hierarchical_summary_response = None
    if dashboard_summary.hierarchical_summary:
        hierarchical_summary_response = _transform_hierarchical_summary(
            dashboard_summary.hierarchical_summary
        )

    # Crear respuesta completa
    return DashboardSummaryResponseByEmployee(
        meta=DashboardSummaryMetaResponseByEmployee(
            users_count=dashboard_summary.meta["users_count"],
            worked_days=dashboard_summary.worked_days,
        ),
        summary=summary_response,
        totals=totals_response,
        hierarchical_summary=hierarchical_summary_response,
    )
