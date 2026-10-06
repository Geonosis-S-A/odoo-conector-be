import pytest
from unittest.mock import Mock

from app.project.api.routers import (
    get_employee_gateway,
    get_project_assignment_gateway,
)
from app.project.domain.gateway import ProjectAssignmentGateway
from app.project.domain.models import Project
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles
from app.users.domain.repositories import EmployeeGateway


@pytest.fixture
def mock_assignment_gateway():
    gw = Mock(spec=ProjectAssignmentGateway)
    gw.get_employee_assigned_projects.return_value = []
    gw.get_managed_projects.return_value = []
    return gw


@pytest.fixture
def mock_employee_gateway():
    gw = Mock(spec=EmployeeGateway)
    gw.get_user_id_by_employee_id.return_value = 100
    return gw


@pytest.fixture(autouse=True)
def setup_dependencies(mock_assignment_gateway, mock_employee_gateway):
    """Configura las dependencias del router para todos los tests de este módulo."""
    from app.main import app

    app.dependency_overrides[get_project_assignment_gateway] = (
        lambda: mock_assignment_gateway
    )
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    yield

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


def _get(test_client):
    return test_client.get(
        "/api/v1/projects/", headers={"Authorization": "Bearer testtoken"}
    )


class TestGetProjects:
    """Cada usuario ve sólo los proyectos a los que está asignado más los que
    gerencia (decisión de gerencia), sin excepción por rol."""

    def test_user_sees_assigned_projects(
        self, mock_assignment_gateway, test_client
    ):
        _override_current_user(test_client, roles=[1])
        mock_assignment_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="Proyecto Alpha"),
            Project(id=2, name="Proyecto Beta"),
        ]

        response = _get(test_client)

        assert response.status_code == 200
        assert [p["id"] for p in response.json()] == [1, 2]
        mock_assignment_gateway.get_employee_assigned_projects.assert_called_once_with(1)

    def test_user_sees_assigned_plus_managed_without_duplicates(
        self, mock_assignment_gateway, test_client
    ):
        _override_current_user(test_client, roles=[1])
        mock_assignment_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="Alpha"),
        ]
        mock_assignment_gateway.get_managed_projects.return_value = [
            Project(id=1, name="Alpha"),
            Project(id=3, name="Gamma"),
        ]

        response = _get(test_client)

        assert response.status_code == 200
        assert sorted(p["id"] for p in response.json()) == [1, 3]
        mock_assignment_gateway.get_managed_projects.assert_called_once_with(100)

    def test_user_without_assignments_sees_empty_list(self, test_client):
        _override_current_user(test_client, roles=[1])

        response = _get(test_client)

        assert response.status_code == 200
        assert response.json() == []

    def test_admin_has_no_exception_and_sees_only_assigned(
        self, mock_assignment_gateway, test_client
    ):
        _override_current_user(test_client, roles=[Roles.approver])
        mock_assignment_gateway.get_employee_assigned_projects.return_value = [
            Project(id=7, name="Mío"),
        ]

        response = _get(test_client)

        assert response.status_code == 200
        assert [p["id"] for p in response.json()] == [7]

    def test_user_without_odoo_user_sees_only_assigned(
        self, mock_assignment_gateway, mock_employee_gateway, test_client
    ):
        _override_current_user(test_client, roles=[1])
        mock_employee_gateway.get_user_id_by_employee_id.return_value = None
        mock_assignment_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="Alpha"),
        ]

        response = _get(test_client)

        assert response.status_code == 200
        assert [p["id"] for p in response.json()] == [1]
        mock_assignment_gateway.get_managed_projects.assert_not_called()

    def test_response_format(self, mock_assignment_gateway, test_client):
        _override_current_user(test_client, roles=[1])
        mock_assignment_gateway.get_employee_assigned_projects.return_value = [
            Project(id=42, name="Proyecto con ID especial")
        ]

        response = _get(test_client)

        data = response.json()
        assert isinstance(data, list)
        assert set(data[0].keys()) == {"id", "name"}
