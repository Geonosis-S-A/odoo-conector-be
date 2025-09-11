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


class GetDashboardSummaryByEmployeeUseCase:
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
        self, employee_id: int, date_from: date, date_to: date
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


        timesheet_data = self.dashboard_gateway.get_timesheet_summary(
            [employee_id],
            date_from,
            date_to,
            self.task_gateway,
            self.timesheet_line_gateway,
        )

        # 3. Calcular KPIs reales
        hours_kpi = self.dashboard_gateway.calculate_hours_kpi(timesheet_data, 1)
        entries_kpi = self.dashboard_gateway.calculate_entries_kpi(timesheet_data, 1)
        daily_average_kpi = self.dashboard_gateway.calculate_daily_average_kpi(
            timesheet_data, 1, date_from, date_to
        )

        # 4. Calcular totales desagregados
        by_project = self.dashboard_gateway.calculate_project_totals(timesheet_data)
        by_task = self.dashboard_gateway.calculate_task_totals(timesheet_data)
        by_employee = self.dashboard_gateway.calculate_employee_totals(timesheet_data, [{"id": employee_id}])

        # 5. Crear y retornar el resumen del dashboard
        dashboard_summary = DashboardSummary.create(
            users_count=1,
            hours_selected_period=hours_kpi,
            entries_selected_period=entries_kpi,
            daily_average_hours=daily_average_kpi,
            by_project=by_project,
            by_task=by_task,
            by_employee=by_employee,
        )

        return dashboard_summary

    