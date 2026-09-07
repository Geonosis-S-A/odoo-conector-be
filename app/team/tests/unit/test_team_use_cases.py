from unittest.mock import Mock

import pytest

from app.team.application.use_cases.get_team import GetTeamUseCase
from app.team.application.use_cases.set_member_permission import (
    SetMemberPermissionUseCase,
)
from app.team.domain.models import PermissionLevel, TeamMemberPermission


class TestGetTeamUseCase:
    def test_enriches_odoo_team_with_permission_levels(self):
        access = Mock()
        access.get_led_team.return_value = [
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

    def test_returns_empty_when_not_a_leader(self):
        access = Mock()
        access.get_led_team.return_value = []
        repo = Mock()

        assert GetTeamUseCase(access, repo).execute(10) == []


class TestSetMemberPermissionUseCase:
    @pytest.fixture
    def access(self):
        a = Mock()
        a.get_led_team_member_ids.return_value = {1, 2, 3}
        return a

    def test_rejects_when_leader_has_no_team(self, access):
        access.get_led_team_member_ids.return_value = set()
        repo = Mock()

        with pytest.raises(ValueError, match="no lidera un equipo"):
            SetMemberPermissionUseCase(access, repo).execute(10, 2, PermissionLevel.view)
        repo.upsert.assert_not_called()

    def test_rejects_member_outside_current_odoo_team(self, access):
        repo = Mock()

        with pytest.raises(ValueError, match="no pertenece al equipo"):
            SetMemberPermissionUseCase(access, repo).execute(
                10, 99, PermissionLevel.view
            )
        repo.upsert.assert_not_called()

    def test_upserts_permission_for_valid_member(self, access):
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
