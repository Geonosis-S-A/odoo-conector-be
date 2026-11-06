from unittest.mock import Mock, patch

import pytest

from app.project.domain.models import Project
from app.team.application import team_access as ta
from app.team.application.team_access import TeamAccessService


@pytest.fixture(autouse=True)
def _cache_activa(monkeypatch):
    # No depender de AUTHZ_CACHE_TTL_SECONDS del entorno donde corran los tests
    for cache in (ta._USER_ID_CACHE, ta._LED_PROJECTS_CACHE, ta._APPROVERS_CACHE):
        monkeypatch.setattr(cache, "ttl_seconds", 60)


@pytest.fixture
def employee_gateway():
    gw = Mock()
    gw.get_user_id_by_employee_id.return_value = 100
    return gw


@pytest.fixture
def assignment_gateway():
    gw = Mock()
    gw.get_led_projects.return_value = [Project(id=7, name="P", manager_user_id=100)]
    gw.get_project_approvers.side_effect = lambda ids: {
        i: [(100, "Gerente")] for i in ids
    }
    return gw


@pytest.fixture
def service(employee_gateway, assignment_gateway):
    return TeamAccessService(
        employee_gateway, assignment_gateway, Mock(), Mock(list_by_member=lambda _: [])
    )


class TestSinCacheEsElComportamientoDeSiempre:
    def test_manages_project_consulta_odoo_cada_vez(
        self, service, employee_gateway, assignment_gateway
    ):
        for _ in range(3):
            assert service.manages_project(5, 7) is True
        assert employee_gateway.get_user_id_by_employee_id.call_count == 3
        assert assignment_gateway.get_led_projects.call_count == 3

    def test_lines_authority_consulta_odoo_cada_vez(
        self, service, employee_gateway, assignment_gateway
    ):
        for _ in range(3):
            service.lines_authority(5, [(8, 7)])
        assert employee_gateway.get_user_id_by_employee_id.call_count == 3
        assert assignment_gateway.get_project_approvers.call_count == 3

    def test_un_cambio_en_odoo_se_ve_de_inmediato(self, service, assignment_gateway):
        assert service.lines_authority(5, [(8, 7)]) == {(8, 7): True}
        # Le sacan la gerencia del proyecto
        assignment_gateway.get_project_approvers.side_effect = lambda ids: {
            i: [(999, "Otro")] for i in ids
        }
        assert service.lines_authority(5, [(8, 7)]) == {(8, 7): False}


class TestConCache:
    def test_manages_project_reusa_lo_ya_consultado(
        self, service, employee_gateway, assignment_gateway
    ):
        for _ in range(3):
            assert service.manages_project(5, 7, cached=True) is True
        assert employee_gateway.get_user_id_by_employee_id.call_count == 1
        assert assignment_gateway.get_led_projects.call_count == 1

    def test_lines_authority_reusa_aprobadores(self, service, assignment_gateway):
        for _ in range(3):
            assert service.lines_authority(5, [(8, 7)], cached=True) == {
                (8, 7): True
            }
        assert assignment_gateway.get_project_approvers.call_count == 1

    def test_approver_names_pide_solo_los_proyectos_que_faltan(
        self, service, assignment_gateway
    ):
        service.project_approver_names([7], cached=True)
        names = service.project_approver_names([7, 8], cached=True)

        assert names == {7: ["Gerente"], 8: ["Gerente"]}
        assert assignment_gateway.get_project_approvers.call_args_list[-1].args == (
            [8],
        )

    def test_el_dato_cacheado_vence_con_el_ttl(self, service, assignment_gateway):
        with patch("app.shared.utils.ttl_cache.time.monotonic", return_value=1000.0):
            service.lines_authority(5, [(8, 7)], cached=True)
        with patch("app.shared.utils.ttl_cache.time.monotonic", return_value=1030.0):
            service.lines_authority(5, [(8, 7)], cached=True)
        assert assignment_gateway.get_project_approvers.call_count == 1

        with patch("app.shared.utils.ttl_cache.time.monotonic", return_value=1061.0):
            service.lines_authority(5, [(8, 7)], cached=True)
        assert assignment_gateway.get_project_approvers.call_count == 2

    def test_no_guarda_user_id_none(self, service, employee_gateway):
        # El gateway devuelve None también ante un error de Odoo
        employee_gateway.get_user_id_by_employee_id.return_value = None
        assert service.manages_project(5, 7, cached=True) is False
        employee_gateway.get_user_id_by_employee_id.return_value = 100
        assert service.manages_project(5, 7, cached=True) is True

    def test_una_falla_de_odoo_no_se_guarda(self, service, assignment_gateway):
        assignment_gateway.get_project_approvers.side_effect = RuntimeError("odoo")
        with pytest.raises(RuntimeError):
            service.project_approver_names([7], cached=True)

        assignment_gateway.get_project_approvers.side_effect = lambda ids: {
            i: [(100, "Gerente")] for i in ids
        }
        assert service.project_approver_names([7], cached=True) == {7: ["Gerente"]}

    def test_ttl_cero_desactiva_la_cache(self, service, employee_gateway, monkeypatch):
        monkeypatch.setattr(ta._USER_ID_CACHE, "ttl_seconds", 0)
        monkeypatch.setattr(ta._LED_PROJECTS_CACHE, "ttl_seconds", 0)
        for _ in range(3):
            service.manages_project(5, 7, cached=True)
        assert employee_gateway.get_user_id_by_employee_id.call_count == 3

    def test_la_cache_es_por_usuario_y_por_proyecto(
        self, service, employee_gateway, assignment_gateway
    ):
        employee_gateway.get_user_id_by_employee_id.side_effect = lambda eid: {
            5: 100,
            6: 200,
        }[eid]
        assignment_gateway.get_led_projects.side_effect = lambda uid: {
            100: [Project(id=7, name="P", manager_user_id=100)],
            200: [],
        }[uid]

        assert service.manages_project(5, 7, cached=True) is True
        assert service.manages_project(6, 7, cached=True) is False
        assert service.manages_project(5, 9, cached=True) is False
