from unittest.mock import Mock

import pytest

from app.project.domain.models import Project
from app.team.application.team_access import LedProjectTeam, TeamMemberInfo
from app.team.application.use_cases.get_team import GetTeamUseCase
from app.team.application.use_cases.get_team_by_project import GetTeamByProjectUseCase
from app.team.application.use_cases.set_member_permission import (
    SetMemberPermissionUseCase,
)
from app.team.domain.models import PermissionLevel, TeamMemberPermission


class TestGetTeamUseCase:
    def test_enriches_pm_candidates_with_permission_levels(self):
        access = Mock()
        access.get_coverage_candidates.return_value = [
            {"id": 1, "name": "Ana", "work_email": "ana@x.com"},
            {"id": 2, "name": "Beto", "work_email": False},
        ]
        repo = Mock()
        repo.list_by_leader.return_value = [
            TeamMemberPermission(
                id=1,
                leader_employee_odoo_id=10,
                member_employee_odoo_id=2,
                level=PermissionLevel.validate,
            )
        ]

        result = GetTeamUseCase(access, repo).execute(10)

        assert [(m.employee_odoo_id, m.level) for m in result] == [
            (1, None),
            (2, PermissionLevel.validate),
        ]
        assert result[1].email is None

    def test_returns_empty_when_there_are_no_pm_candidates(self):
        access = Mock()
        access.get_coverage_candidates.return_value = []
        repo = Mock()

        assert GetTeamUseCase(access, repo).execute(10) == []


class TestGetTeamByProjectUseCase:
    def test_delegates_to_team_access(self):
        access = Mock()
        expected = [
            LedProjectTeam(
                project=Project(id=1, name="P1", manager_user_id=100),
                members=[
                    TeamMemberInfo(
                        employee_odoo_id=2, name="Ana", email="ana@x.com", level=None
                    )
                ],
            )
        ]
        access.get_led_team_by_project.return_value = expected

        result = GetTeamByProjectUseCase(access).execute(10)

        assert result == expected
        access.get_led_team_by_project.assert_called_once_with(10)


class TestSetMemberPermissionUseCase:
    @pytest.fixture
    def access(self):
        a = Mock()
        a.is_project_head.return_value = True
        # PM de los proyectos que gerencia el líder 10
        a.get_coverage_candidates.return_value = [
            {"id": 1, "name": "Ana", "work_email": "ana@x.com"},
            {"id": 2, "name": "Beto", "work_email": "beto@x.com"},
        ]
        return a

    def test_rejects_when_leader_is_not_a_project_head(self, access):
        access.is_project_head.return_value = False
        repo = Mock()

        with pytest.raises(ValueError, match="gerentes de proyectos"):
            SetMemberPermissionUseCase(access, repo).execute(10, 2, PermissionLevel.view)
        repo.upsert.assert_not_called()

    def test_rejects_member_who_is_not_a_pm_of_the_leader_projects(self, access):
        repo = Mock()

        with pytest.raises(ValueError, match="no es PM de ninguno"):
            SetMemberPermissionUseCase(access, repo).execute(
                10, 99, PermissionLevel.view
            )
        repo.upsert.assert_not_called()

    def test_upserts_permission_for_a_pm_of_the_leader(self, access):
        repo = Mock()

        SetMemberPermissionUseCase(access, repo).execute(10, 2, PermissionLevel.validate)

        assert repo.upsert.call_count == 1
        saved = repo.upsert.call_args[0][0]
        assert saved.leader_employee_odoo_id == 10
        assert saved.member_employee_odoo_id == 2
        assert saved.level == PermissionLevel.validate

    def test_level_none_deletes_permission(self, access):
        repo = Mock()

        result = SetMemberPermissionUseCase(access, repo).execute(10, 2, None)

        assert result is None
        repo.delete.assert_called_once_with(10, 2)
        repo.upsert.assert_not_called()

    def test_level_none_deletes_even_if_the_member_is_no_longer_a_pm(self, access):
        # Una delegación vieja tiene que poder quitarse aunque la persona ya no
        # sea PM de sus proyectos (o el líder ya no gerencie ninguno).
        access.is_project_head.return_value = False
        access.get_coverage_candidates.return_value = []
        repo = Mock()

        SetMemberPermissionUseCase(access, repo).execute(10, 99, None)

        repo.delete.assert_called_once_with(10, 99)
