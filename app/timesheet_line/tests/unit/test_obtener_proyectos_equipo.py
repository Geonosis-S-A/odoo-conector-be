from datetime import date
from unittest.mock import Mock

from app.project.domain.models import Project
from app.timesheet_line.application.use_cases.obtener_proyectos_equipo import (
    GetTeamProjectsUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine


def _line(line_id: int, employee_id: int, project: Project) -> DetailedTimesheetLine:
    return DetailedTimesheetLine(
        id=line_id,
        name=f"ts-{line_id}",
        employee_id=employee_id,
        project=project,
        task=None,
        hours=8.0,
        date=date(2026, 9, 1),
        validated=False,
    )


class TestGetTeamProjectsUseCase:
    def test_returns_empty_when_no_validatable_team(self):
        team_access = Mock()
        team_access.validatable_employee_ids.return_value = set()
        gateway = Mock()

        use_case = GetTeamProjectsUseCase(team_access, gateway)
        result = use_case.execute(10)

        assert result == []
        gateway.all.assert_not_called()

    def test_returns_distinct_projects_from_team_timesheet_lines(self):
        team_access = Mock()
        team_access.validatable_employee_ids.return_value = {1, 2}
        gateway = Mock()
        project_a = Project(id=100, name="Proyecto A")
        project_b = Project(id=200, name="Proyecto B")
        gateway.all.return_value = [
            _line(1, employee_id=1, project=project_a),
            _line(2, employee_id=2, project=project_a),  # mismo proyecto, dedup
            _line(3, employee_id=2, project=project_b),
        ]

        use_case = GetTeamProjectsUseCase(team_access, gateway)
        result = use_case.execute(10, date(2026, 9, 1), date(2026, 9, 30))

        assert {p.id for p in result} == {100, 200}
        gateway.all.assert_called_once_with(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 30),
            team=True,
            team_members_ids=[1, 2],
        )
        team_access.validatable_employee_ids.assert_called_once_with(
            10, date(2026, 9, 1), date(2026, 9, 30)
        )
