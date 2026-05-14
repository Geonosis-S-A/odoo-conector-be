"""Regresión VT-17: export vía sólo ``all_by_employees``, sin el OR por proyectos gestionados."""

from datetime import date
from unittest.mock import Mock

from app.dashboard.application.use_cases.export_timesheets import (
    ExportTimesheetsByTeamUseCase,
)


def test_execute_uses_all_by_employees_and_not_managed_projects_path():
    timesheet_gateway = Mock()
    timesheet_gateway.all_by_employees.return_value = []
    timesheet_gateway.all_by_employees_with_requester_user_id = Mock()

    uc = ExportTimesheetsByTeamUseCase(
        timesheet_gateway,
        Mock(),
        [10, 20, 30],
        employee_price_repository=None,
    )
    uc.execute(date(2026, 1, 1), date(2026, 1, 31))

    timesheet_gateway.all_by_employees.assert_called_once_with(
        [10, 20, 30], date(2026, 1, 1), date(2026, 1, 31)
    )
    timesheet_gateway.all_by_employees_with_requester_user_id.assert_not_called()
