import pytest
from unittest.mock import Mock

from app.project.api.routers import get_project_gateway, router
from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles


@pytest.fixture
def mock_gateway():
    """Fixture que proporciona un gateway de proyectos mockeado."""
    return Mock(spec=ProjectGateway)


@pytest.fixture(autouse=True)
def setup_dependencies(mock_gateway):
    """Configura las dependencias del router para todos los tests de este módulo."""
    from app.main import app

    app.dependency_overrides[get_project_gateway] = lambda: mock_gateway

    yield

    app.dependency_overrides.pop(get_project_gateway, None)


def _override_current_user(test_client, *, roles):
    async def _override():
        return {
            "user_id": 1,
            "user_email": "test@example.com",
            "user_name": "Test User",
            "roles": roles,
        }

    test_client.app.dependency_overrides[get_current_user] = _override


class TestGetProjects:
    """Cualquier usuario autenticado ve todos los proyectos activos, sin
    filtrar por asignación: `project.assignment` está lejos de cubrir a
    todos los empleados que realmente trabajan en un proyecto."""

    def test_regular_user_sees_all_active_projects(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[1])
        mock_projects = [
            Project(id=1, name="Proyecto Alpha"),
            Project(id=2, name="Proyecto Beta"),
            Project(id=3, name="Proyecto Gamma"),
        ]
        mock_gateway.all.return_value = mock_projects

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Proyecto Alpha"
        mock_gateway.all.assert_called_once_with()

    def test_admin_sees_same_list_as_regular_user(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[Roles.approver])
        mock_gateway.all.return_value = [Project(id=1, name="Proyecto Alpha")]

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_projects_empty_returns_empty_array(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[1])
        mock_gateway.all.return_value = []

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_projects_handles_none_from_gateway(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[1])
        mock_gateway.all.return_value = None

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_projects_duplicate_handling_in_use_case(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[1])
        mock_gateway.all.return_value = [
            Project(id=1, name="Proyecto Alpha"),
            Project(id=2, name="Proyecto Beta"),
            Project(id=1, name="Proyecto Alpha Duplicado"),
        ]

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        project_ids = {p["id"] for p in data}
        assert project_ids == {1, 2}

    def test_get_projects_response_format(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[1])
        mock_gateway.all.return_value = [Project(id=42, name="Proyecto con ID especial")]

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert set(data[0].keys()) == {"id", "name"}
