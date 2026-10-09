"""El suplente ve y abre los proyectos del líder que le delegó la aprobación,
solo mientras la delegación está vigente."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.project.domain.models import Project
from app.team.application.team_access import TeamAccessService
from app.team.domain.models import PermissionLevel, TeamMemberPermission

HOY = date.today()
AYER = HOY - timedelta(days=1)
EN_UNA_SEMANA = HOY + timedelta(days=7)

LIDER, SUPLENTE, ANA, OTRO = 10, 2, 1, 3
P_LIDER, P_PROPIO = 1, 5


def _emp(i, name):
    return SimpleNamespace(id=i, full_name=name, email=f"{name.lower()}@x.com")


def _perm(level=PermissionLevel.validate, valid_from=None, valid_until=EN_UNA_SEMANA):
    return TeamMemberPermission(
        None, LIDER, SUPLENTE, level, valid_from=valid_from, valid_until=valid_until
    )


@pytest.fixture
def permissions():
    """Permisos que recibió cada empleado; los tests los cambian."""
    return {SUPLENTE: [_perm()]}


@pytest.fixture
def service(permissions):
    employee_gateway = Mock()
    employee_gateway.get_user_id_by_employee_id.side_effect = (
        lambda eid: {LIDER: 100, SUPLENTE: 20, OTRO: 30}.get(eid)
    )
    employee_gateway.get_by_ids.side_effect = lambda ids: [
        _emp(i, {LIDER: "Lider", SUPLENTE: "Suplente", ANA: "Ana"}.get(i, f"E{i}"))
        for i in ids
    ]

    assignment_gateway = Mock()
    assignment_gateway.is_project_manager_only.return_value = False
    # El líder (user 100) gerencia P_LIDER; el suplente (user 20) gerencia P_PROPIO.
    assignment_gateway.get_led_projects.side_effect = lambda uid: {
        100: [Project(id=P_LIDER, name="Del líder", manager_user_id=100)],
        20: [Project(id=P_PROPIO, name="Propio", manager_user_id=20)],
    }.get(uid, [])
    assignment_gateway.get_project_approvers.return_value = {
        P_LIDER: [(100, "Lider")],
        P_PROPIO: [(20, "Suplente")],
    }
    assignment_gateway.get_team_users.side_effect = (
        lambda user_id, emp_id, date_from=None, date_to=None, only_active=False: (
            [{"id": SUPLENTE, "name": "Suplente", "work_email": "s@x.com"}]
            if emp_id == LIDER
            else []
        )
    )
    assignment_gateway.get_project_assignments.return_value = [
        {"employee_id": [ANA, "Ana"], "project_id": [P_LIDER, "Del líder"]},
        {"employee_id": [LIDER, "Lider"], "project_id": [P_LIDER, "Del líder"]},
        {"employee_id": [SUPLENTE, "Suplente"], "project_id": [P_LIDER, "Del líder"]},
        {"employee_id": [ANA, "Ana"], "project_id": [P_PROPIO, "Propio"]},
    ]
    timesheet_gateway = Mock()
    timesheet_gateway.get_team_users.return_value = []
    month = HOY.replace(day=1).isoformat()
    timesheet_gateway.get_pending_lines_minimal.return_value = [
        {"employee_id": [ANA, "Ana"], "project_id": [P_LIDER, "x"], "date": month},
        # Horas del propio líder que delegó: no las puede aprobar el suplente
        {"employee_id": [LIDER, "Lider"], "project_id": [P_LIDER, "x"], "date": month},
    ]

    repo = Mock()
    repo.list_by_member.side_effect = lambda member_id: permissions.get(member_id, [])
    return TeamAccessService(employee_gateway, assignment_gateway, timesheet_gateway, repo)


def _by_id(projects):
    return {p.project.id: p for p in projects}


class TestVistaPorProyecto:
    def test_el_suplente_ve_los_proyectos_del_lider_ademas_de_los_suyos(self, service):
        projects = _by_id(service.get_led_team_by_project(SUPLENTE))

        assert set(projects) == {P_PROPIO, P_LIDER}

    def test_indica_a_quien_cubre_y_hasta_cuando(self, service):
        projects = _by_id(service.get_led_team_by_project(SUPLENTE))

        cubierto = projects[P_LIDER]
        assert cubierto.covering_leader_id == LIDER
        assert cubierto.covering_leader_name == "Lider"
        assert cubierto.covering_until == EN_UNA_SEMANA

    def test_el_proyecto_propio_no_figura_como_cubierto(self, service):
        propio = _by_id(service.get_led_team_by_project(SUPLENTE))[P_PROPIO]

        assert propio.covering_leader_id is None
        assert propio.covering_leader_name is None
        assert propio.covering_until is None

    def test_no_muestra_ni_cuenta_las_horas_de_quien_delego(self, service):
        cubierto = _by_id(service.get_led_team_by_project(SUPLENTE))[P_LIDER]

        # Ni el líder que delegó ni el propio suplente entre los miembros...
        assert {m.employee_odoo_id for m in cubierto.members} == {ANA}
        # ...y de las dos pendientes (Ana y el líder) solo cuenta la de Ana.
        assert cubierto.pending_count == 1

    def test_sin_cobertura_solo_ve_los_suyos(self, service, permissions):
        permissions.clear()

        assert set(_by_id(service.get_led_team_by_project(SUPLENTE))) == {P_PROPIO}

    def test_un_permiso_vencido_no_da_acceso_a_los_proyectos_del_lider(
        self, service, permissions
    ):
        permissions[SUPLENTE] = [_perm(valid_until=AYER)]

        assert set(_by_id(service.get_led_team_by_project(SUPLENTE))) == {P_PROPIO}

    def test_un_permiso_solo_de_vista_no_da_acceso(self, service, permissions):
        permissions[SUPLENTE] = [_perm(level=PermissionLevel.view)]

        assert set(_by_id(service.get_led_team_by_project(SUPLENTE))) == {P_PROPIO}

    def test_un_permiso_que_todavia_no_empezo_no_da_acceso(self, service, permissions):
        permissions[SUPLENTE] = [_perm(valid_from=EN_UNA_SEMANA, valid_until=None)]

        assert set(_by_id(service.get_led_team_by_project(SUPLENTE))) == {P_PROPIO}

    def test_el_lider_sigue_viendo_su_proyecto_completo(self, service):
        # El líder no tiene permisos recibidos: se comporta como antes.
        projects = _by_id(service.get_led_team_by_project(LIDER))

        assert set(projects) == {P_LIDER}
        assert projects[P_LIDER].covering_leader_id is None


class TestAccesoAlProyecto:
    def test_el_suplente_puede_abrir_el_proyecto_del_lider(self, service):
        assert service.can_access_project(SUPLENTE, P_LIDER) is True

    def test_y_el_suyo(self, service):
        assert service.can_access_project(SUPLENTE, P_PROPIO) is True

    def test_no_un_proyecto_ajeno(self, service):
        assert service.can_access_project(SUPLENTE, 99) is False

    def test_quien_no_recibio_permiso_no_entra(self, service):
        assert service.can_access_project(OTRO, P_LIDER) is False

    def test_vencida_la_cobertura_ya_no_puede_abrirlo(self, service, permissions):
        permissions[SUPLENTE] = [_perm(valid_until=AYER)]

        assert service.can_access_project(SUPLENTE, P_LIDER) is False

    def test_el_acceso_para_ver_no_habilita_aprobar_lo_ajeno(self, service):
        # Aunque abra el tablero, validar/borrar se decide línea por línea.
        result = service.lines_authority(SUPLENTE, [(ANA, P_LIDER), (LIDER, P_LIDER)])

        assert result[(ANA, P_LIDER)] is True
        assert result[(LIDER, P_LIDER)] is False  # nunca las horas de quien delegó


class TestCacheDeLaCobertura:
    def test_con_cache_no_repite_la_consulta_de_permisos(self, service, monkeypatch):
        from app.team.application import team_access as ta

        monkeypatch.setattr(ta._COVERAGE_CACHE, "ttl_seconds", 60)
        service._coverages(SUPLENTE, cached=True)
        service._coverages(SUPLENTE, cached=True)

        assert service.permission_repo.list_by_member.call_count == 1

    def test_sin_cache_consulta_siempre(self, service):
        service._coverages(SUPLENTE)
        service._coverages(SUPLENTE)

        assert service.permission_repo.list_by_member.call_count == 2
