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
    def project_assignment_gateway(self):
        gw = Mock()
        # equipo (proyectos gerenciados) por líder (excluye siempre al propio líder)
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
        gw.get_team_users.side_effect = (
            lambda user_id, emp_id, date_from=None, date_to=None: teams.get(
                emp_id, []
            )
        )
        return gw

    @pytest.fixture
    def timesheet_line_gateway(self):
        gw = Mock()
        # Sin equipo por jerarquía ni pendientes por defecto; los tests que
        # los necesiten sobreescriben `side_effect`/`return_value`.
        gw.get_team_users.return_value = []
        gw.get_pending_lines_minimal.return_value = []
        return gw

    @pytest.fixture
    def permission_repo(self):
        return Mock()

    @pytest.fixture
    def service(
        self,
        employee_gateway,
        project_assignment_gateway,
        timesheet_line_gateway,
        permission_repo,
    ):
        return TeamAccessService(
            employee_gateway,
            project_assignment_gateway,
            timesheet_line_gateway,
            permission_repo,
        )

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

    def test_get_led_team_by_project_groups_members_and_excludes_leader(
        self, service, project_assignment_gateway
    ):
        from app.project.domain.models import Project
        from app.users.domain.models import Employee

        project_assignment_gateway.get_managed_projects.return_value = [
            Project(id=1, name="P1", manager_user_id=100),
            Project(id=2, name="P2", manager_user_id=100),
        ]
        project_assignment_gateway.get_project_assignments.return_value = [
            {"employee_id": [1, "Ana"], "project_id": [1, "P1"]},
            {"employee_id": [2, "Beto"], "project_id": [1, "P1"]},
            {"employee_id": [10, "Lider"], "project_id": [2, "P2"]},  # el propio líder
            {"employee_id": [4, "Dino"], "project_id": [2, "P2"]},
        ]
        service.employee_gateway.get_by_ids.return_value = [
            Employee(id=1, email="ana@x.com", full_name="Ana"),
            Employee(id=2, email="beto@x.com", full_name="Beto"),
            Employee(id=4, email="dino@x.com", full_name="Dino"),
        ]

        result = service.get_led_team_by_project(10)

        assert {t.project.id for t in result} == {1, 2}
        by_project = {t.project.id: t for t in result}
        assert {m.employee_odoo_id for m in by_project[1].members} == {1, 2}
        assert {m.employee_odoo_id for m in by_project[2].members} == {4}

    def test_get_led_team_by_project_no_managed_projects_returns_empty(
        self, service, project_assignment_gateway
    ):
        project_assignment_gateway.get_managed_projects.return_value = []

        assert service.get_led_team_by_project(10) == []

    def test_get_led_team_by_project_leader_without_odoo_user(self, service):
        assert service.get_led_team_by_project(99) == []

    def test_get_led_team_by_project_project_without_assignments_has_empty_members(
        self, service, project_assignment_gateway
    ):
        from app.project.domain.models import Project

        project_assignment_gateway.get_managed_projects.return_value = [
            Project(id=1, name="P1", manager_user_id=100),
        ]
        project_assignment_gateway.get_project_assignments.return_value = []

        result = service.get_led_team_by_project(10)

        assert len(result) == 1
        assert result[0].project.id == 1
        assert result[0].members == []

    def test_get_led_team_by_project_counts_pending_lines_per_project(
        self, service, project_assignment_gateway, timesheet_line_gateway
    ):
        from app.project.domain.models import Project
        from app.users.domain.models import Employee

        project_assignment_gateway.get_managed_projects.return_value = [
            Project(id=1, name="P1", manager_user_id=100),
            Project(id=2, name="P2", manager_user_id=100),
        ]
        project_assignment_gateway.get_project_assignments.return_value = [
            {"employee_id": [1, "Ana"], "project_id": [1, "P1"]},
            {"employee_id": [2, "Beto"], "project_id": [2, "P2"]},
        ]
        service.employee_gateway.get_by_ids.return_value = [
            Employee(id=1, email="ana@x.com", full_name="Ana"),
            Employee(id=2, email="beto@x.com", full_name="Beto"),
        ]
        timesheet_line_gateway.get_pending_lines_minimal.return_value = [
            {"employee_id": [1, "Ana"], "project_id": [1, "P1"]},
            {"employee_id": [1, "Ana"], "project_id": [1, "P1"]},
            {"employee_id": [1, "Ana"], "project_id": [1, "P1"]},
            # Beto no está asignado a P1: no debe sumar a P1 aunque tenga
            # horas pendientes cargadas ahí (p.ej. validable por jerarquía).
            {"employee_id": [2, "Beto"], "project_id": [1, "P1"]},
        ]

        result = service.get_led_team_by_project(10)

        by_project = {t.project.id: t for t in result}
        assert by_project[1].pending_count == 3
        assert by_project[2].pending_count == 0
        timesheet_line_gateway.get_pending_lines_minimal.assert_called_once()
        called_employee_ids, called_project_ids = (
            timesheet_line_gateway.get_pending_lines_minimal.call_args[0]
        )
        assert set(called_employee_ids) == {1, 2}
        assert set(called_project_ids) == {1, 2}

    # ------------------------------------------------------------------
    # Unión jerarquía (Odoo timesheet_manager_id/child_of) ∪ proyectos
    # ------------------------------------------------------------------
    def test_get_led_team_includes_hierarchy_only_members(
        self, service, project_assignment_gateway, timesheet_line_gateway, permission_repo
    ):
        # Líder sin proyectos gerenciados, pero con equipo por jerarquía en Odoo
        project_assignment_gateway.get_team_users.side_effect = (
            lambda user_id, emp_id, date_from=None, date_to=None: []
        )
        timesheet_line_gateway.get_team_users.side_effect = (
            lambda user_id, emp_id: [{"id": 5, "name": "Eva", "work_email": "eva@x.com"}]
            if emp_id == 10
            else []
        )
        permission_repo.list_by_member.return_value = []

        assert service.get_led_team_member_ids(10) == {5}
        assert service.is_leader(10) is True
        assert service.validatable_employee_ids(10) == {5}

    def test_get_led_team_dedupes_member_in_both_hierarchy_and_project(
        self, service, timesheet_line_gateway, permission_repo
    ):
        # Cira (3) ya está en el equipo por proyecto del líder 10; también
        # aparece por jerarquía: no debe duplicarse.
        timesheet_line_gateway.get_team_users.side_effect = (
            lambda user_id, emp_id: [{"id": 3, "name": "Cira", "work_email": "cira@x.com"}]
            if emp_id == 10
            else []
        )
        permission_repo.list_by_member.return_value = []

        team = service.get_led_team(10)
        assert sorted(u["id"] for u in team) == [1, 2, 3]

    # ------------------------------------------------------------------
    # Equipo acotado a un proyecto puntual (solo project.assignment)
    # ------------------------------------------------------------------
    def test_manages_project_true_when_project_in_managed_list(
        self, service, project_assignment_gateway
    ):
        from app.project.domain.models import Project

        project_assignment_gateway.get_managed_projects.return_value = [
            Project(id=139, name="Mesa evolutiva", manager_user_id=100),
        ]

        assert service.manages_project(10, 139) is True
        project_assignment_gateway.get_managed_projects.assert_called_once_with(100)

    def test_manages_project_false_when_not_in_managed_list(
        self, service, project_assignment_gateway
    ):
        project_assignment_gateway.get_managed_projects.return_value = []

        assert service.manages_project(10, 139) is False

    def test_manages_project_false_when_leader_has_no_odoo_user(self, service):
        assert service.manages_project(99, 139) is False

    def test_project_assigned_employee_ids_reads_project_assignment(
        self, service, project_assignment_gateway
    ):
        project_assignment_gateway.get_project_assignments.return_value = [
            {"employee_id": [30, "Marta"], "project_id": [139, "Mesa evolutiva"]},
            {"employee_id": [31, "Nico"], "project_id": [139, "Mesa evolutiva"]},
        ]

        ids = service.project_assigned_employee_ids(139)

        assert ids == {30, 31}
        project_assignment_gateway.get_project_assignments.assert_called_once_with(
            [139], None, None
        )

    # ------------------------------------------------------------------
    # Autoridad por línea: gerente del proyecto de cada línea
    # ------------------------------------------------------------------
    def test_lines_authority_manager_of_project_can_act(
        self, service, project_assignment_gateway, permission_repo
    ):
        permission_repo.list_by_member.return_value = []
        # proyecto 1 lo gerencia el user 100 (líder 10); proyecto 2 el user 200
        project_assignment_gateway.get_project_manager_user_ids.return_value = {
            1: 100,
            2: 200,
        }

        result = service.lines_authority(10, [(1, 1), (1, 2), (3, 1)])

        assert result == {(1, 1): True, (1, 2): False, (3, 1): True}
        # una sola lectura de gerentes para todas las líneas
        project_assignment_gateway.get_project_manager_user_ids.assert_called_once_with(
            [1, 2]
        )

    def test_lines_authority_never_on_own_lines(
        self, service, project_assignment_gateway, permission_repo
    ):
        permission_repo.list_by_member.return_value = []
        project_assignment_gateway.get_project_manager_user_ids.return_value = {1: 100}

        assert service.can_act_on_line(10, 10, 1) is False

    def test_lines_authority_hierarchy_only_when_project_has_no_manager(
        self, service, project_assignment_gateway, timesheet_line_gateway, permission_repo
    ):
        permission_repo.list_by_member.return_value = []
        project_assignment_gateway.get_project_manager_user_ids.return_value = {
            1: None,
            2: 200,
        }
        timesheet_line_gateway.get_team_users.return_value = [{"id": 1}]

        result = service.lines_authority(10, [(1, 1), (3, 1), (1, 2)])

        # sin gerente: valida el jefe por jerarquía, sólo de su gente
        assert result[(1, 1)] is True
        assert result[(3, 1)] is False
        # con gerente ajeno: la jerarquía NO alcanza
        assert result[(1, 2)] is False

    def test_lines_authority_hierarchy_does_not_override_other_manager(
        self, service, project_assignment_gateway, timesheet_line_gateway, permission_repo
    ):
        permission_repo.list_by_member.return_value = []
        project_assignment_gateway.get_project_manager_user_ids.return_value = {5: 200}
        timesheet_line_gateway.get_team_users.return_value = [{"id": 1}]

        # 1 está bajo la jerarquía del 10, pero el proyecto lo gerencia el user 200
        assert service.can_act_on_line(10, 1, 5) is False

    def test_lines_authority_delegated_validate_acts_with_leader_projects(
        self, service, project_assignment_gateway, permission_repo
    ):
        permission_repo.list_by_member.return_value = [
            _perm(10, 2, PermissionLevel.validate)
        ]
        project_assignment_gateway.get_project_manager_user_ids.return_value = {
            1: 100,
            2: 200,
        }

        result = service.lines_authority(2, [(1, 1), (1, 2), (10, 1)])

        assert result[(1, 1)] is True   # proyecto del líder que delegó
        assert result[(1, 2)] is False  # proyecto de otro líder
        assert result[(10, 1)] is False  # nunca las horas del propio líder

    def test_lines_authority_view_permission_does_not_grant_action(
        self, service, project_assignment_gateway, permission_repo
    ):
        permission_repo.list_by_member.return_value = [_perm(10, 2, PermissionLevel.view)]
        project_assignment_gateway.get_project_manager_user_ids.return_value = {1: 100}

        assert service.can_act_on_line(2, 1, 1) is False

    def test_lines_authority_actor_without_authority_reads_nothing(
        self, service, project_assignment_gateway, permission_repo
    ):
        permission_repo.list_by_member.return_value = []

        result = service.lines_authority(99, [(1, 1)])

        assert result == {(1, 1): False}
        project_assignment_gateway.get_project_manager_user_ids.assert_not_called()
