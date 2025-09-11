from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Path

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
)
from app.dashboard.application.use_cases.get_dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from app.dashboard.application.use_cases.get_dashboard_summary_by_employee import (
    GetDashboardSummaryByEmployeeUseCase,
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
        return OdooDashboardDataService(odoo_connection, employee_gateway, task_gateway, timesheet_line_gateway)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de dashboard"
        )


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
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
            dashboard_gateway, employee_gateway, task_gateway, timesheet_line_gateway
        )
        dashboard_summary = use_case.execute(user_id, requester_employee_id, date_from, date_to)
        # Transformar modelo de dominio a esquema de respuesta
        response = _transform_to_response_schema(dashboard_summary)

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


def _transform_to_response_schema(dashboard_summary) -> DashboardSummaryResponse:
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
            )
            for employee in dashboard_summary.totals["by_employee"]
        ],
    )

    # Crear respuesta completa
    return DashboardSummaryResponse(
        meta=DashboardSummaryMetaResponse(
            users_count=dashboard_summary.meta["users_count"]
        ),
        summary=summary_response,
        totals=totals_response,
    )


def _transform_to_response_schema_by_employee(dashboard_summary) -> DashboardSummaryResponseByEmployee:
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
            )
            for employee in dashboard_summary.totals["by_employee"]
        ],
    )

    # Crear respuesta completa
    return DashboardSummaryResponseByEmployee(
        meta=DashboardSummaryMetaResponseByEmployee(
            users_count=dashboard_summary.meta["users_count"],
            worked_days=dashboard_summary.worked_days,
        ),
        summary=summary_response,
        totals=totals_response,
    )