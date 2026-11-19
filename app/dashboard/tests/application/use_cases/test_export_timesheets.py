from datetime import date
from unittest.mock import Mock

import pytest

from app.dashboard.application.use_cases.export_timesheets import (
    ExportTimesheetsByTeamUseCase,
)

LINE = {
    "id": 1,
    "name": "x",
    "date": "2024-01-10",
    "unit_amount": 2.0,
    "employee_id": [7, "Luca"],
    "project_id": [152, "Proyecto"],
    "task_id": False,
    "create_date": "2024-01-10 10:00:00",
    "validated": False,
}


class TestExportTimesheetsByTeamUseCase:
    """El Excel usa la misma regla de equipo que el resumen del dashboard."""

    @pytest.fixture
    def gateways(self):
        timesheet = Mock()
        timesheet.get_team_users.return_value = [{"id": 1}, {"id": 2}]
        timesheet.all_by_employees_with_requester_user_id.return_value = [LINE]
        employee = Mock()
        employee.get_user_id_by_employee_id.return_value = 42
        task = Mock()
        assignment = Mock()
        return timesheet, employee, task, assignment

    def _use_case(self, gateways):
        timesheet, employee, task, assignment = gateways
        return ExportTimesheetsByTeamUseCase(timesheet, employee, task, 10, assignment)

    def test_pm_puro_no_suma_jerarquia(self, gateways):
        timesheet, _, _, assignment = gateways
        assignment.is_project_manager_only.return_value = True

        self._use_case(gateways).execute(date(2024, 1, 1), date(2024, 1, 31))

        assignment.is_project_manager_only.assert_called_once_with(42)
        timesheet.get_team_users.assert_not_called()
        timesheet.all_by_employees_with_requester_user_id.assert_called_once_with(
            [], date(2024, 1, 1), date(2024, 1, 31), 42
        )

    def test_delivery_suma_jerarquia(self, gateways):
        timesheet, _, _, assignment = gateways
        assignment.is_project_manager_only.return_value = False

        self._use_case(gateways).execute(date(2024, 1, 1), date(2024, 1, 31))

        timesheet.get_team_users.assert_called_once_with(42, 10)
        timesheet.all_by_employees_with_requester_user_id.assert_called_once_with(
            [1, 2], date(2024, 1, 1), date(2024, 1, 31), 42
        )
