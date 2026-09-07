from unittest.mock import Mock

import pytest

from app.team.application.team_access import TeamAccessService
from app.team.domain.models import PermissionLevel, TeamMemberPermission


def _perm(leader: int, member: int, level: PermissionLevel) -> TeamMemberPermission:
    return TeamMemberPermission(
        id=None,
        leader_employee_odoo_id=leader,
        member_employee_odoo_id=member,
        level=level,
    )


class TestTeamAccessService:
    @pytest.fixture
    def employee_gateway(self):
        gw = Mock()
        # leader 10 -> user 100 ; leader 20 -> user 200 ; leader 99 -> sin usuario
        gw.get_user_id_by_employee_id.side_effect = lambda eid: {
            10: 100,
            20: 200,
            99: None,
        }.get(eid)
        return gw

    @pytest.fixture
    def timesheet_gateway(self):
        gw = Mock()
        # equipo Odoo por líder (excluye siempre al propio líder)
        teams = {
            10: [
                {"id": 1, "name": "Ana", "work_email": "ana@x.com"},
                {"id": 2, "name": "Beto", "work_email": "beto@x.com"},
                {"id": 3, "name": "Cira", "work_email": False},
            ],
            20: [
                {"id": 3, "name": "Cira", "work_email": "cira@x.com"},
                {"id": 4, "name": "Dino", "work_email": "dino@x.com"},
            ],
        }
        gw.get_team_users.side_effect = lambda user_id, emp_id: teams.get(emp_id, [])
        return gw

    @pytest.fixture
    def permission_repo(self):
        return Mock()

    @pytest.fixture
    def service(self, employee_gateway, timesheet_gateway, permission_repo):
        return TeamAccessService(employee_gateway, timesheet_gateway, permission_repo)

    def test_leader_sees_and_validates_own_odoo_team(self, service, permission_repo):
        permission_repo.list_by_member.return_value = []

        assert service.is_leader(10) is True
        assert service.visible_employee_ids(10) == {1, 2, 3}
        assert service.validatable_employee_ids(10) == {1, 2, 3}

    def test_non_leader_without_permissions_has_nothing(self, service, permission_repo):
        permission_repo.list_by_member.return_value = []

        assert service.is_leader(1) is False
        assert service.visible_employee_ids(1) == set()
        assert service.can_view_team(1) is False
        assert service.can_validate_team(1) is False

    def test_member_with_view_permission_sees_team_minus_leader_and_self(
        self, service, permission_repo
    ):
        # Beto (2) recibe 'view' del líder 10
        permission_repo.list_by_member.return_value = [_perm(10, 2, PermissionLevel.view)]

        assert service.visible_employee_ids(2) == {1, 3}
        # 'view' no habilita validación
        assert service.validatable_employee_ids(2) == set()
        assert service.can_validate_team(2) is False

    def test_member_with_validate_permission_can_validate_team(
        self, service, permission_repo
    ):
        permission_repo.list_by_member.return_value = [
            _perm(10, 2, PermissionLevel.validate)
        ]

        assert service.validatable_employee_ids(2) == {1, 3}
        # nunca puede validarse a sí mismo
        assert 2 not in service.validatable_employee_ids(2)

    def test_permission_ignored_when_member_no_longer_in_odoo_team(
        self, service, permission_repo
    ):
        # Dino (4) tiene permiso del líder 10, pero el equipo Odoo de 10 no lo incluye
        permission_repo.list_by_member.return_value = [
            _perm(10, 4, PermissionLevel.validate)
        ]

        assert service.validatable_employee_ids(4) == set()
        assert service.visible_employee_ids(4) == set()

    def test_multiple_leaders_union(self, service, permission_repo):
        # Cira (3) está en el equipo de 10 y de 20; recibe validate de ambos
        permission_repo.list_by_member.return_value = [
            _perm(10, 3, PermissionLevel.validate),
            _perm(20, 3, PermissionLevel.validate),
        ]

        # team(10)={1,2,3} menos {10,3} = {1,2} ; team(20)={3,4} menos {20,3} = {4}
        assert service.validatable_employee_ids(3) == {1, 2, 4}

    def test_leader_without_odoo_user_has_no_team(self, service, permission_repo):
        permission_repo.list_by_member.return_value = []

        assert service.get_led_team(99) == []
        assert service.is_leader(99) is False

    def test_visible_team_members_for_leader(self, service, permission_repo):
        permission_repo.list_by_member.return_value = []

        members = service.visible_team_members(10)
        by_id = {m.employee_odoo_id: m for m in members}
        assert set(by_id) == {1, 2, 3}
        assert by_id[1].name == "Ana"
        assert by_id[1].email == "ana@x.com"
        assert by_id[3].email is None  # work_email False -> None
        assert all(m.level is None for m in members)

    def test_visible_team_members_for_member_with_permission(
        self, service, permission_repo
    ):
        permission_repo.list_by_member.return_value = [
            _perm(10, 2, PermissionLevel.view)
        ]

        members = service.visible_team_members(2)
        assert {m.employee_odoo_id for m in members} == {1, 3}

    def test_visible_team_members_empty_when_no_access(self, service, permission_repo):
        permission_repo.list_by_member.return_value = []

        assert service.visible_team_members(1) == []
