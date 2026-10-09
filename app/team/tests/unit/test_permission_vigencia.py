"""Vigencia (valid_from / valid_until) de los permisos delegados: fuera de su
ventana un permiso no concede nada; dentro, se comporta como siempre."""

from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from app.team.application.team_access import TeamAccessService
from app.team.domain.models import PermissionLevel, TeamMemberPermission

HOY = date.today()
AYER = HOY - timedelta(days=1)
MANANA = HOY + timedelta(days=1)


def _perm(level=PermissionLevel.validate, valid_from=None, valid_until=None):
    return TeamMemberPermission(
        id=None,
        leader_employee_odoo_id=10,
        member_employee_odoo_id=2,
        level=level,
        valid_from=valid_from,
        valid_until=valid_until,
    )


class TestIsActive:
    def test_sin_fechas_nunca_vence(self):
        assert _perm().is_active(HOY) is True
        assert _perm().is_active(date(2099, 1, 1)) is True

    def test_los_extremos_son_inclusivos(self):
        p = _perm(valid_from=HOY, valid_until=HOY)
        assert p.is_active(HOY) is True
        assert p.is_active(AYER) is False
        assert p.is_active(MANANA) is False

    def test_solo_desde_no_tiene_fin(self):
        p = _perm(valid_from=HOY)
        assert p.is_active(AYER) is False
        assert p.is_active(date(2099, 1, 1)) is True

    def test_solo_hasta_no_tiene_inicio(self):
        p = _perm(valid_until=HOY)
        assert p.is_active(date(2000, 1, 1)) is True
        assert p.is_active(MANANA) is False


class TestVigenciaEnElAcceso:
    @pytest.fixture
    def employee_gateway(self):
        gw = Mock()
        gw.get_user_id_by_employee_id.side_effect = lambda eid: {10: 100, 2: 20}.get(eid)
        return gw

    @pytest.fixture
    def project_assignment_gateway(self):
        gw = Mock()
        team_of_10 = [
            {"id": 1, "name": "Ana", "work_email": "ana@x.com"},
            {"id": 2, "name": "Beto", "work_email": "beto@x.com"},
        ]
        gw.is_project_manager_only.return_value = False
        gw.get_project_approvers.return_value = {1: [(100, "Líder")]}
        gw.get_team_users.side_effect = (
            lambda user_id, emp_id, date_from=None, date_to=None, only_active=False: (
                team_of_10 if emp_id == 10 else []
            )
        )
        return gw

    @pytest.fixture
    def permission_repo(self):
        return Mock()

    @pytest.fixture
    def service(self, employee_gateway, project_assignment_gateway, permission_repo):
        timesheet_gw = Mock()
        timesheet_gw.get_team_users.return_value = []
        return TeamAccessService(
            employee_gateway, project_assignment_gateway, timesheet_gw, permission_repo
        )

    @pytest.mark.parametrize(
        "valid_from, valid_until, vigente",
        [
            (None, None, True),  # sin fechas: como siempre
            (AYER, MANANA, True),  # dentro de la ventana
            (HOY, HOY, True),  # solo hoy
            (AYER, AYER, False),  # ya venció
            (MANANA, None, False),  # todavía no empezó
        ],
    )
    def test_la_autoridad_delegada_solo_aplica_dentro_de_la_ventana(
        self, service, permission_repo, valid_from, valid_until, vigente
    ):
        permission_repo.list_by_member.return_value = [
            _perm(valid_from=valid_from, valid_until=valid_until)
        ]

        result = service.lines_authority(2, [(1, 1)])

        assert result[(1, 1)] is vigente

    def test_un_permiso_vencido_tampoco_deja_ver_ni_validar_al_equipo(
        self, service, permission_repo
    ):
        permission_repo.list_by_member.return_value = [_perm(valid_until=AYER)]

        assert service.visible_employee_ids(2) == set()
        assert service.validatable_employee_ids(2) == set()
        assert service.can_view_team(2) is False
        assert service.visible_team_members(2) == []

    def test_un_permiso_vigente_sigue_dando_vista_y_validacion(
        self, service, permission_repo
    ):
        permission_repo.list_by_member.return_value = [
            _perm(valid_from=AYER, valid_until=MANANA)
        ]

        assert service.visible_employee_ids(2) == {1}
        assert service.validatable_employee_ids(2) == {1}

    def test_con_dos_permisos_solo_cuenta_el_vigente(self, service, permission_repo):
        vencido = _perm(valid_until=AYER)
        vigente = TeamMemberPermission(
            id=None,
            leader_employee_odoo_id=10,
            member_employee_odoo_id=2,
            level=PermissionLevel.validate,
            valid_from=AYER,
            valid_until=MANANA,
        )
        permission_repo.list_by_member.return_value = [vencido, vigente]

        assert service.lines_authority(2, [(1, 1)])[(1, 1)] is True
