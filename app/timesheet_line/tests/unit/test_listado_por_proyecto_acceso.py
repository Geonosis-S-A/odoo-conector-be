"""GET /timesheet/ con team=true:

- por PROYECTO el acceso lo decide el caso de uso (can_access_project); el router
  no resuelve antes el equipo completo (varias consultas a Odoo);
- en la vista plana (sin proyecto) el router sigue exigiendo equipo visible.
"""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.security.dependencies import get_current_user
from app.team.api.dependencies import get_team_access_service
from app.timesheet_line.api import routers as timesheet_routers

USER = 5
BASE = {"date_from": "2026-10-01", "date_to": "2026-10-09"}


@pytest.fixture
def ctx():
    team_access = Mock()
    team_access.can_view_team.return_value = True
    team_access.can_access_project.return_value = True
    team_access.visible_employee_ids.return_value = {1, 2}
    team_access.lines_authority.return_value = {}
    team_access.project_approver_names.return_value = {}

    gateway = Mock()
    gateway.all.return_value = []
    notifications = Mock()
    notifications.get_by_timesheet_ids.return_value = []
    employee_gateway = Mock()
    employee_gateway.exists_by_id.return_value = True

    app.dependency_overrides[get_current_user] = lambda: {"user_id": USER, "roles": []}
    app.dependency_overrides[get_team_access_service] = lambda: team_access
    app.dependency_overrides[timesheet_routers.get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[timesheet_routers.get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[timesheet_routers.get_notification_repository] = lambda: notifications
    app.dependency_overrides[timesheet_routers.get_task_gateway] = lambda: Mock()
    try:
        yield Mock(client=TestClient(app), team_access=team_access, gateway=gateway)
    finally:
        app.dependency_overrides.clear()


class TestPorProyecto:
    def test_no_resuelve_el_equipo_completo_antes_del_caso_de_uso(self, ctx):
        response = ctx.client.get(
            "/api/v1/timesheet/", params={**BASE, "team": "true", "project_id": 115}
        )

        assert response.status_code == 200
        ctx.team_access.can_view_team.assert_not_called()
        ctx.team_access.visible_employee_ids.assert_not_called()

    def test_el_acceso_lo_decide_can_access_project(self, ctx):
        ctx.client.get(
            "/api/v1/timesheet/", params={**BASE, "team": "true", "project_id": 115}
        )

        ctx.team_access.can_access_project.assert_called_once_with(
            USER, 115, cached=True
        )

    def test_sin_acceso_al_proyecto_es_403_y_no_lee_horas(self, ctx):
        ctx.team_access.can_access_project.return_value = False

        response = ctx.client.get(
            "/api/v1/timesheet/", params={**BASE, "team": "true", "project_id": 115}
        )

        assert response.status_code == 403
        ctx.gateway.all.assert_not_called()

    def test_la_lista_de_empleados_asignados_no_condiciona_el_acceso(self, ctx):
        # Un PM sin personas asignadas igual puede ver las horas de su proyecto
        ctx.team_access.can_view_team.return_value = False

        response = ctx.client.get(
            "/api/v1/timesheet/", params={**BASE, "team": "true", "project_id": 115}
        )

        assert response.status_code == 200


class TestVistaPlana:
    def test_sigue_exigiendo_equipo_visible(self, ctx):
        ctx.team_access.can_view_team.return_value = False

        response = ctx.client.get("/api/v1/timesheet/", params={**BASE, "team": "true"})

        assert response.status_code == 403
        ctx.team_access.can_view_team.assert_called_once_with(USER)
        ctx.gateway.all.assert_not_called()

    def test_con_equipo_visible_responde(self, ctx):
        response = ctx.client.get("/api/v1/timesheet/", params={**BASE, "team": "true"})

        assert response.status_code == 200
        ctx.team_access.can_view_team.assert_called_once_with(USER)


class TestHorasPropias:
    def test_las_propias_no_consultan_el_equipo(self, ctx):
        response = ctx.client.get(
            "/api/v1/timesheet/", params={**BASE, "employee_id": USER}
        )

        assert response.status_code == 200
        ctx.team_access.can_view_team.assert_not_called()

    def test_ver_a_otro_sin_team_es_403(self, ctx):
        response = ctx.client.get(
            "/api/v1/timesheet/", params={**BASE, "employee_id": 99}
        )

        assert response.status_code == 403
