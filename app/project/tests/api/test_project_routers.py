import pytest
from unittest.mock import Mock

from app.project.api.routers import (
    get_employee_gateway,
    get_project_assignment_gateway,
    get_project_gateway,
    router,
)
from app.project.domain.gateway import ProjectAssignmentGateway, ProjectGateway
from app.project.domain.models import Project
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles
from app.users.domain.repositories import EmployeeGateway


@pytest.fixture
def mock_gateway():
    """Fixture que proporciona un gateway de proyectos mockeado."""
    return Mock(spec=ProjectGateway)


@pytest.fixture
def mock_project_assignment_gateway():
    return Mock(spec=ProjectAssignmentGateway)


@pytest.fixture
def mock_employee_gateway():
    gw = Mock(spec=EmployeeGateway)
    gw.get_user_id_by_employee_id.return_value = 100
    return gw


@pytest.fixture(autouse=True)
def setup_dependencies(mock_gateway, mock_project_assignment_gateway, mock_employee_gateway):
    """Configura las dependencias del router para todos los tests de este módulo."""
    from app.main import app

    app.dependency_overrides[get_project_gateway] = lambda: mock_gateway
    app.dependency_overrides[get_project_assignment_gateway] = (
        lambda: mock_project_assignment_gateway
    )
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    yield

    app.dependency_overrides.pop(get_project_gateway, None)
    app.dependency_overrides.pop(get_project_assignment_gateway, None)
    app.dependency_overrides.pop(get_employee_gateway, None)


def _override_current_user(test_client, *, roles):
    async def _override():
        return {
            "user_id": 1,
            "user_email": "test@example.com",
            "user_name": "Test User",
            "roles": roles,
        }

    test_client.app.dependency_overrides[get_current_user] = _override


class TestGetProjectsAsAdmin:
    """Un admin (rol approver) ve todos los proyectos activos, sin filtrar."""

    def test_get_all_active_projects_success(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[Roles.approver])
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

    def test_get_projects_empty_returns_empty_array(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[Roles.approver])
        mock_gateway.all.return_value = []

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_projects_handles_none_from_gateway(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[Roles.approver])
        mock_gateway.all.return_value = None

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_projects_duplicate_handling_in_use_case(self, mock_gateway, test_client):
        _override_current_user(test_client, roles=[Roles.approver])
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
        _override_current_user(test_client, roles=[Roles.approver])
        mock_gateway.all.return_value = [Project(id=42, name="Proyecto con ID especial")]

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert set(data[0].keys()) == {"id", "name"}


class TestGetProjectsAsRegularUser:
    """Un usuario no-admin ve sólo los proyectos a los que está asignado o que gerencia."""

    def test_returns_assigned_and_managed_projects(
        self, mock_project_assignment_gateway, mock_employee_gateway, test_client
    ):
        _override_current_user(test_client, roles=[1])
        mock_project_assignment_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="Proyecto Asignado"),
        ]
        mock_project_assignment_gateway.get_managed_projects.return_value = [
            Project(id=2, name="Proyecto Gerenciado", manager_user_id=100),
        ]

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        data = response.json()
        assert {p["id"] for p in data} == {1, 2}
        mock_project_assignment_gateway.get_employee_assigned_projects.assert_called_once_with(
            1
        )
        mock_project_assignment_gateway.get_managed_projects.assert_called_once_with(100)
        mock_employee_gateway.get_user_id_by_employee_id.assert_called_once_with(1)

    def test_deduplicates_project_assigned_and_managed_at_once(
        self, mock_project_assignment_gateway, test_client
    ):
        _override_current_user(test_client, roles=[1])
        mock_project_assignment_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="Proyecto Compartido"),
        ]
        mock_project_assignment_gateway.get_managed_projects.return_value = [
            Project(id=1, name="Proyecto Compartido", manager_user_id=100),
        ]

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_empty_when_no_assignments_and_no_user_id(
        self, mock_project_assignment_gateway, mock_employee_gateway, test_client
    ):
        _override_current_user(test_client, roles=[1])
        mock_employee_gateway.get_user_id_by_employee_id.return_value = None
        mock_project_assignment_gateway.get_employee_assigned_projects.return_value = []

        response = test_client.get(
            "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
        )

        assert response.status_code == 200
        assert response.json() == []
        mock_project_assignment_gateway.get_managed_projects.assert_not_called()

    def test_does_not_call_unrestricted_project_gateway(
        self, mock_gateway, mock_project_assignment_gateway, test_client
    ):
        _override_current_user(test_client, roles=[1])
        mock_project_assignment_gateway.get_employee_assigned_projects.return_value = []
        mock_project_assignment_gateway.get_managed_projects.return_value = []

        test_client.get("/api/v1/projects/", headers={"Authorization": "Bearer testtoken"})

        mock_gateway.all.assert_not_called()
