from datetime import date
from unittest.mock import Mock

import pytest

from app.project.domain.models import Project
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetDeleteError,
    TimesheetDeleteForbiddenError,
    TimesheetNotFoundError,
)
from app.timesheet_line.application.use_cases.delete_timesheet import (
    DeleteTimesheetUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway


def _line(line_id: int, employee_id: int, project_id: int = 1, validated: bool = False):
    return DetailedTimesheetLine(
        id=line_id,
        name=f"ts-{line_id}",
        employee_id=employee_id,
        project=Project(id=project_id, name="P"),
        task=None,
        hours=8.0,
        date=date(2026, 9, 8),
        validated=validated,
    )


@pytest.fixture
def gateway():
    gw = Mock(spec=TimesheetLineGateway)
    gw.delete.return_value = True
    return gw


class TestDeleteTimesheetUseCase:
    def test_not_found(self, gateway):
        gateway.get_by_ids.return_value = []
        with pytest.raises(TimesheetNotFoundError):
            DeleteTimesheetUseCase(gateway).execute([1])
        gateway.delete.assert_not_called()

    def test_without_requester_keeps_legacy_behaviour(self, gateway):
        gateway.get_by_ids.return_value = [_line(1, 7)]
        assert DeleteTimesheetUseCase(gateway, Mock()).execute([1]) is True

    def test_owner_can_delete_own_pending_line(self, gateway):
        gateway.get_by_ids.return_value = [_line(1, 5)]
        team_access = Mock()
        team_access.lines_authority.return_value = {(5, 1): False}

        assert DeleteTimesheetUseCase(gateway, team_access).execute(
            [1], requester_employee_id=5
        )
        gateway.delete.assert_called_once_with([1])

    def test_owner_cannot_delete_own_validated_line(self, gateway):
        gateway.get_by_ids.return_value = [_line(1, 5, validated=True)]
        team_access = Mock()
        team_access.lines_authority.return_value = {(5, 1): False}

        with pytest.raises(TimesheetDeleteForbiddenError):
            DeleteTimesheetUseCase(gateway, team_access).execute(
                [1], requester_employee_id=5
            )
        gateway.delete.assert_not_called()

    def test_project_manager_can_delete_team_line(self, gateway):
        gateway.get_by_ids.return_value = [_line(1, 7, project_id=3)]
        team_access = Mock()
        team_access.lines_authority.return_value = {(7, 3): True}

        assert DeleteTimesheetUseCase(gateway, team_access).execute(
            [1], requester_employee_id=5
        )

    def test_third_party_cannot_delete_and_nothing_is_deleted(self, gateway):
        # una línea permitida + una ajena: no se borra ninguna
        gateway.get_by_ids.return_value = [
            _line(1, 7, project_id=3),
            _line(2, 8, project_id=4),
        ]
        team_access = Mock()
        team_access.lines_authority.return_value = {(7, 3): True, (8, 4): False}

        with pytest.raises(TimesheetDeleteForbiddenError) as exc:
            DeleteTimesheetUseCase(gateway, team_access).execute(
                [1, 2], requester_employee_id=5
            )
        assert "[2]" in exc.value.message
        gateway.delete.assert_not_called()

    def test_odoo_failure_is_wrapped(self, gateway):
        gateway.get_by_ids.return_value = [_line(1, 5)]
        gateway.delete.side_effect = Exception("boom")
        team_access = Mock()
        team_access.lines_authority.return_value = {}

        with pytest.raises(TimesheetDeleteError):
            DeleteTimesheetUseCase(gateway, team_access).execute(
                [1], requester_employee_id=5
            )
