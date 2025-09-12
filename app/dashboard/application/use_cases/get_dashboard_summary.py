from datetime import date
from typing import List

from app.dashboard.domain.models import (
    DashboardSummary,
    KPI,
    ProjectTotal,
    TaskTotal,
    EmployeeTotal,
)
from app.dashboard.domain.repositories import DashboardDataService
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.users.domain.repositories import EmployeeGateway
from app.task.domain.gateway import TaskGateway
from app.timesheet_line.domain.repositories import TimesheetLineGateway


class GetDashboardSummaryUseCase:
    """Caso de uso para obtener el resumen del dashboard del equipo."""

    def __init__(
        self,
        dashboard_gateway: DashboardDataService,
        employee_gateway: EmployeeGateway,
        task_gateway: TaskGateway,
        timesheet_line_gateway: TimesheetLineGateway,
    ):
        self.dashboard_gateway = dashboard_gateway
        self.employee_gateway = employee_gateway
        self.task_gateway = task_gateway
        self.timesheet_line_gateway = timesheet_line_gateway

    def execute(
        self, user_id: int, employee_id: int, date_from: date, date_to: date
    ) -> DashboardSummary:
        """
        Ejecuta el caso de uso para obtener el resumen del dashboard.

        Args:
            user_id: ID del usuario que solicita el dashboard
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            DashboardSummary con todos los KPIs y totales calculados
        """

        users = self.timesheet_line_gateway.get_team_users(user_id, employee_id)

        users_count = len(users)

        ids = [user["id"] for user in users]

        timesheet_data = self.dashboard_gateway.get_timesheet_summary(
            ids,
            date_from,
            date_to,
            self.task_gateway,
            self.timesheet_line_gateway,
        )

        # 3. Calcular KPIs reales
        hours_kpi = self.dashboard_gateway.calculate_hours_kpi(
            timesheet_data, users_count
        )
        entries_kpi = self.dashboard_gateway.calculate_entries_kpi(
            timesheet_data, users_count
        )
        daily_average_kpi = self.dashboard_gateway.calculate_daily_average_kpi(
            timesheet_data, users_count, date_from, date_to
        )

        # 4. Calcular totales desagregados
        by_project = self.dashboard_gateway.calculate_project_totals(timesheet_data)
        by_task = self.dashboard_gateway.calculate_task_totals(timesheet_data)
        by_employee = self.dashboard_gateway.calculate_employee_totals(
            timesheet_data, users
        )

        # 5. Calcular horas cargadas a proyectos sin tarea específica
        by_project_without_task = (
            self.dashboard_gateway.calculate_project_without_task_totals(
                by_project, by_task
            )
        )

        "append de by_project_without_task a by_task"
        by_task.extend(by_project_without_task)

        # 6. Calcular nueva estructura jerárquica
        hierarchical_summary = self.dashboard_gateway.calculate_hierarchical_summary(
            timesheet_data, self.task_gateway
        )

        # 7. Crear y retornar el resumen del dashboard
        dashboard_summary = DashboardSummary.create(
            users_count=users_count,
            hours_selected_period=hours_kpi,
            entries_selected_period=entries_kpi,
            daily_average_hours=daily_average_kpi,
            by_project=by_project,
            by_task=by_task,
            by_employee=by_employee,
            hierarchical_summary=hierarchical_summary,
        )

        return dashboard_summary
