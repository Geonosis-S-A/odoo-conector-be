"""La cobertura de aprobaciones es solo para deliveries (gerentes de proyectos) y
solo se delega en los PM de sus proyectos."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.security.dependencies import get_current_user
from app.team.api.dependencies import (
    get_permission_repository,
    get_team_access_service,
)
from app.team.application.team_access import TeamAccessService

LIDER, PM_A, PM_B = 10, 2, 3


class TestCoverageCandidates:
    @pytest.fixture
    def service(self):
        employee_gateway = Mock()
        employee_gateway.get_user_id_by_employee_id.side_effect = (
            lambda eid: {LIDER: 100, PM_A: 20}.get(eid)
        )
        assignment_gateway = Mock()
        assignment_gateway.get_managed_project_pms.return_value = [
            {"id": PM_A, "name": "Paulo", "work_email": "p@x.com"},
            {"id": PM_B, "name": "Valentina", "work_email": "v@x.com"},
        ]
        return TeamAccessService(employee_gateway, assignment_gateway, Mock(), Mock()), (
            assignment_gateway
        )

    def test_son_los_pm_de_los_proyectos_que_gerencia(self, service):
        svc, assignment_gateway = service

        candidates = svc.get_coverage_candidates(LIDER)

        assert [u["id"] for u in candidates] == [PM_A, PM_B]
        assignment_gateway.get_managed_project_pms.assert_called_once_with(100)

    def test_nunca_se_incluye_al_propio_lider(self, service):
        svc, assignment_gateway = service
        assignment_gateway.get_managed_project_pms.return_value = [
            {"id": LIDER, "name": "Laura", "work_email": "l@x.com"},
            {"id": PM_A, "name": "Paulo", "work_email": "p@x.com"},
        ]

        assert [u["id"] for u in svc.get_coverage_candidates(LIDER)] == [PM_A]

    def test_sin_usuario_en_odoo_no_hay_candidatos(self, service):
        svc, assignment_gateway = service

        assert svc.get_coverage_candidates(99) == []
        assignment_gateway.get_managed_project_pms.assert_not_called()

    def test_un_delivery_sin_pm_en_sus_proyectos_tiene_lista_vacia(self, service):
        svc, assignment_gateway = service
        assignment_gateway.get_managed_project_pms.return_value = []

        assert svc.get_coverage_candidates(LIDER) == []

    def test_se_consulta_odoo_cada_vez(self, service):
        # De esto depende que una delegación siga valiendo: nada de caché.
        svc, assignment_gateway = service

        svc.get_coverage_candidates(LIDER)
        svc.get_coverage_candidates(LIDER)

        assert assignment_gateway.get_managed_project_pms.call_count == 2


class TestEndpointsDeCobertura:
    @pytest.fixture
    def ctx(self):
        access = Mock()
        access.is_project_head.return_value = True
        access.get_coverage_candidates.return_value = [
            {"id": PM_A, "name": "Paulo", "work_email": "p@x.com"},
        ]
        repo = Mock()
        repo.list_by_leader.return_value = []
        repo.upsert.side_effect = lambda p: p
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": LIDER,
            "roles": [],
        }
        app.dependency_overrides[get_team_access_service] = lambda: access
        app.dependency_overrides[get_permission_repository] = lambda: repo
        try:
            yield Mock(client=TestClient(app), access=access, repo=repo)
        finally:
            app.dependency_overrides.clear()

    def test_el_delivery_ve_solo_a_sus_pm(self, ctx):
        response = ctx.client.get("/api/v1/teams/mine")

        assert response.status_code == 200
        assert [m["employee_odoo_id"] for m in response.json()["members"]] == [PM_A]

    def test_un_delivery_sin_pms_recibe_lista_vacia_no_error(self, ctx):
        ctx.access.get_coverage_candidates.return_value = []

        response = ctx.client.get("/api/v1/teams/mine")

        assert response.status_code == 200
        assert response.json()["members"] == []

    def test_quien_no_es_gerente_de_proyectos_recibe_403(self, ctx):
        ctx.access.is_project_head.return_value = False

        response = ctx.client.get("/api/v1/teams/mine")

        assert response.status_code == 403
        assert "gerentes de proyectos" in response.json()["detail"]

    def test_un_pm_no_puede_delegar(self, ctx):
        ctx.access.is_project_head.return_value = False

        response = ctx.client.put(
            f"/api/v1/teams/mine/members/{PM_B}", json={"level": "validate"}
        )

        assert response.status_code == 403
        ctx.repo.upsert.assert_not_called()

    def test_delegar_en_alguien_que_no_es_pm_de_sus_proyectos_es_400(self, ctx):
        response = ctx.client.put(
            f"/api/v1/teams/mine/members/{PM_B}", json={"level": "validate"}
        )

        assert response.status_code == 400
        assert "no es PM" in response.json()["detail"]
        ctx.repo.upsert.assert_not_called()

    def test_quitar_una_delegacion_vieja_se_permite_aunque_ya_no_gerencie(self, ctx):
        ctx.access.is_project_head.return_value = False
        ctx.access.get_coverage_candidates.return_value = []

        response = ctx.client.put(
            f"/api/v1/teams/mine/members/{PM_B}", json={"level": "none"}
        )

        assert response.status_code == 200
        assert response.json()["level"] is None
        ctx.repo.delete.assert_called_once_with(LIDER, PM_B)
