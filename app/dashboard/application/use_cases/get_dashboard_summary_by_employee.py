from datetime import date
from typing import List, Optional

from app.dashboard.domain.models import (
    DashboardSummaryByEmployee,
    PreviousPeriodData,
    ValidationStats,
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
        dashboard_service: DashboardDataService,
        employee_gateway: EmployeeGateway,
        task_gateway: TaskGateway,
        timesheet_line_gateway: TimesheetLineGateway,
    ):
        self.dashboard_service = dashboard_service
        self.employee_gateway = employee_gateway
        self.task_gateway = task_gateway
        self.timesheet_line_gateway = timesheet_line_gateway

    def execute(
        self,
        employee_id: int,
        date_from: date,
        date_to: date,
        prev_date_from: Optional[date] = None,
        prev_date_to: Optional[date] = None,
    ) -> DashboardSummaryByEmployee:
        """
        Ejecuta el caso de uso para obtener el resumen del dashboard.

        Args:
            user_id: ID del usuario que solicita el dashboard
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            DashboardSummary con todos los KPIs y totales calculados
        """

        all_timesheet_data = self.dashboard_service.get_timesheet_summary(
            [employee_id],
            date_from,
            date_to,
            self.task_gateway,
            self.timesheet_line_gateway,
            None,
        )

        # Excluir registros del proyecto interno (licencias, vacaciones, ausencias)
        # para que no distorsionen ninguna métrica del dashboard.
        INTERNAL_PROJECT_NAME = "Interno"
        timesheet_data = [
            line for line in all_timesheet_data
            if line.project.name != INTERNAL_PROJECT_NAME
        ]

        dias_trabajados = {line.date for line in timesheet_data if line.hours > 0}
        dias_trabajados_count = len(dias_trabajados)
        # 3. Calcular KPIs reales
        hours_kpi = self.dashboard_service.calculate_hours_kpi(timesheet_data, 1)
        entries_kpi = self.dashboard_service.calculate_entries_kpi(timesheet_data, 1)
        daily_average_kpi = self.dashboard_service.calculate_daily_average_kpi(
            timesheet_data, 1, date_from, date_to
        )

        # 4. Calcular totales desagregados
        by_project = self.dashboard_service.calculate_project_totals(timesheet_data)
        by_task = self.dashboard_service.calculate_task_totals(timesheet_data)
        by_employee = self.dashboard_service.calculate_employee_totals(
            timesheet_data, [{"id": employee_id}]
        )

        # 5. Calcular horas cargadas a proyectos sin tarea específica
        by_project_without_task = (
            self.dashboard_service.calculate_project_without_task_totals(
                by_project, by_task
            )
        )

        "append de by_project_without_task a by_task"
        by_task.extend(by_project_without_task)

        # 6. Calcular nueva estructura jerárquica
        hierarchical_summary = self.dashboard_service.calculate_hierarchical_summary(
            timesheet_data, self.task_gateway
        )

        # 7. Calcular estadísticas de validación
        approved_hours = sum(line.hours for line in timesheet_data if line.validated)
        pending_hours = sum(line.hours for line in timesheet_data if not line.validated)
        validation_stats = ValidationStats(
            approved_hours=approved_hours,
            pending_hours=pending_hours,
        )

        # 8. Crear el resumen del dashboard
        dashboard_summary = DashboardSummaryByEmployee.create(
            users_count=1,
            worked_days=dias_trabajados_count,
            hours_selected_period=hours_kpi,
            entries_selected_period=entries_kpi,
            daily_average_hours=daily_average_kpi,
            by_project=by_project,
            by_task=by_task,
            by_employee=by_employee,
            hierarchical_summary=hierarchical_summary,
        )
        dashboard_summary.validation_stats = validation_stats

        # 9. Computar período anterior si se solicitó (solo KPIs, sin jerarquía)
        if prev_date_from and prev_date_to:
            dashboard_summary.previous_period = self._compute_previous_period(
                employee_id, prev_date_from, prev_date_to
            )

        return dashboard_summary

    def _compute_previous_period(
        self, employee_id: int, date_from: date, date_to: date
    ) -> PreviousPeriodData:
        """Computa los KPIs mínimos del período anterior (sin jerarquía ni totales)."""
        INTERNAL_PROJECT_NAME = "Interno"

        all_data = self.dashboard_service.get_timesheet_summary(
            [employee_id], date_from, date_to,
            self.task_gateway, self.timesheet_line_gateway, None,
        )
        data = [line for line in all_data if line.project.name != INTERNAL_PROJECT_NAME]

        worked_days = len({line.date for line in data if line.hours > 0})
        hours_kpi = self.dashboard_service.calculate_hours_kpi(data, 1)
        entries_kpi = self.dashboard_service.calculate_entries_kpi(data, 1)
        daily_avg_kpi = self.dashboard_service.calculate_daily_average_kpi(
            data, 1, date_from, date_to
        )

        return PreviousPeriodData(
            worked_days=worked_days,
            hours_total=hours_kpi.total,
            entries_total=entries_kpi.total,
            daily_average=daily_avg_kpi.total,
        )
