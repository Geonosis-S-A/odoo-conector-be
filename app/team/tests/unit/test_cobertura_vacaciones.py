"""Cobertura de aprobaciones: el líder delega con fechas, el suplente no puede
volver a delegar y el equipo devuelve la vigencia de cada permiso."""

from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from app.team.application.team_access import TeamAccessService
from app.team.application.use_cases.get_team import GetTeamUseCase
from app.team.application.use_cases.set_member_permission import (
    SetMemberPermissionUseCase,
)
from app.team.domain.models import PermissionLevel, TeamMemberPermission

HOY = date.today()
AYER = HOY - timedelta(days=1)
MANANA = HOY + timedelta(days=1)
EN_UNA_SEMANA = HOY + timedelta(days=7)


@pytest.fixture
def team_access():
    ta = Mock()
    ta.get_led_team_member_ids.return_value = {1, 2, 3}
    return ta


@pytest.fixture
def repo():
    r = Mock()
    r.upsert.side_effect = lambda p: p
    return r


class TestSetMemberPermissionConFechas:
    def test_guarda_la_vigencia(self, team_access, repo):
        SetMemberPermissionUseCase(team_access, repo).execute(
            10, 2, PermissionLevel.validate, MANANA, EN_UNA_SEMANA
        )

        saved = repo.upsert.call_args.args[0]
        assert saved.valid_from == MANANA
        assert saved.valid_until == EN_UNA_SEMANA
        assert saved.level == PermissionLevel.validate

    def test_sin_fechas_no_vence(self, team_access, repo):
        SetMemberPermissionUseCase(team_access, repo).execute(
            10, 2, PermissionLevel.validate
        )

        saved = repo.upsert.call_args.args[0]
        assert saved.valid_from is None and saved.valid_until is None

    def test_rechaza_desde_posterior_a_hasta(self, team_access, repo):
        with pytest.raises(ValueError, match="desde"):
            SetMemberPermissionUseCase(team_access, repo).execute(
                10, 2, PermissionLevel.validate, EN_UNA_SEMANA, MANANA
            )
        repo.upsert.assert_not_called()

    def test_rechaza_hasta_en_el_pasado(self, team_access, repo):
        with pytest.raises(ValueError, match="ya pasó"):
            SetMemberPermissionUseCase(team_access, repo).execute(
                10, 2, PermissionLevel.validate, None, AYER
            )
        repo.upsert.assert_not_called()

    def test_hasta_hoy_es_valido(self, team_access, repo):
        SetMemberPermissionUseCase(team_access, repo).execute(
            10, 2, PermissionLevel.validate, HOY, HOY
        )
        repo.upsert.assert_called_once()

    def test_quitar_el_permiso_ignora_las_fechas(self, team_access, repo):
        SetMemberPermissionUseCase(team_access, repo).execute(
            10, 2, None, EN_UNA_SEMANA, AYER
        )
        repo.delete.assert_called_once_with(10, 2)
        repo.upsert.assert_not_called()

    def test_solo_se_delega_a_gente_de_su_equipo(self, team_access, repo):
        with pytest.raises(ValueError, match="no pertenece"):
            SetMemberPermissionUseCase(team_access, repo).execute(
                10, 99, PermissionLevel.validate, HOY, EN_UNA_SEMANA
            )


class TestGetTeamDevuelveLaVigencia:
    def test_incluye_las_fechas_aunque_el_permiso_este_vencido(self):
        team_access = Mock()
        team_access.get_led_team.return_value = [
            {"id": 2, "name": "Beto", "work_email": "b@x.com"},
            {"id": 3, "name": "Cira", "work_email": False},
        ]
        repo = Mock()
        repo.list_by_leader.return_value = [
            TeamMemberPermission(
                id=1,
                leader_employee_odoo_id=10,
                member_employee_odoo_id=2,
                level=PermissionLevel.validate,
                valid_from=date(2026, 1, 5),
                valid_until=AYER,  # vencido: el líder igual debe verlo
            )
        ]

        beto, cira = GetTeamUseCase(team_access, repo).execute(10)

        assert (beto.level, beto.valid_from, beto.valid_until) == (
            PermissionLevel.validate,
            date(2026, 1, 5),
            AYER,
        )
        assert (cira.level, cira.valid_from, cira.valid_until) == (None, None, None)


class TestElSuplenteNoDelegaALoSuyo:
    """Líder 10 (user 100) -> Beto 2 (user 20) -> Cira 3 (user 30)."""

    @pytest.fixture
    def service(self):
        employee_gateway = Mock()
        employee_gateway.get_user_id_by_employee_id.side_effect = (
            lambda eid: {10: 100, 2: 20, 3: 30}.get(eid)
        )
        assignment_gateway = Mock()
        assignment_gateway.is_project_manager_only.return_value = False
        # Proyecto 1: solo lo aprueba el líder 10 (user 100).
        assignment_gateway.get_project_approvers.return_value = {1: [(100, "Líder")]}
        teams = {
            10: [{"id": 2, "name": "Beto", "work_email": "b@x.com"}],
            2: [{"id": 3, "name": "Cira", "work_email": "c@x.com"}],
        }
        assignment_gateway.get_team_users.side_effect = (
            lambda user_id, emp_id, date_from=None, date_to=None, only_active=False: (
                teams.get(emp_id, [])
            )
        )
        timesheet_gateway = Mock()
        timesheet_gateway.get_team_users.return_value = []

        permissions = {
            2: [  # Beto recibió 'validate' del líder 10
                TeamMemberPermission(
                    None, 10, 2, PermissionLevel.validate, valid_until=EN_UNA_SEMANA
                )
            ],
            3: [  # Cira recibió 'validate' de Beto (que solo tiene lo delegado)
                TeamMemberPermission(None, 2, 3, PermissionLevel.validate)
            ],
        }
        repo = Mock()
        repo.list_by_member.side_effect = lambda member_id: permissions.get(member_id, [])
        return TeamAccessService(
            employee_gateway, assignment_gateway, timesheet_gateway, repo
        )

    def test_el_suplente_si_aprueba_en_los_proyectos_del_lider(self, service):
        # Línea de otra persona (empleado 7) en el proyecto 1 del líder
        assert service.lines_authority(2, [(7, 1)])[(7, 1)] is True

    def test_quien_recibe_permiso_del_suplente_no_hereda_la_autoridad_del_lider(
        self, service
    ):
        # Cira solo tiene permiso de Beto, y Beto no es aprobador del proyecto 1:
        # la autoridad del líder 10 no se transmite.
        assert service.lines_authority(3, [(7, 1)])[(7, 1)] is False
