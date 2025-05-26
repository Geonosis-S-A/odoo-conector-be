import pytest
from unittest.mock import Mock, patch
from app.task.api.routers import router, get_task_gateway
from app.task.domain.models import Task
from app.task.domain.gateway import TaskGateway
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection_dependency


@pytest.fixture
def mock_gateway():
    """Fixture que proporciona un gateway mockeado."""
    return Mock(spec=TaskGateway)


@pytest.fixture
def mock_odoo_connection():
    """Fixture que proporciona una conexión Odoo mockeada."""
    return {
        "uid": 1,
        "models": Mock(),
        "ODOO_DB": "test_db",
        "ODOO_PASSWORD": "test_pass",
    }


@pytest.fixture(autouse=True)
def setup_dependencies(mock_odoo_connection, mock_gateway):
    """Fixture que configura las dependencias para todos los tests."""
    from app.main import app

    # Mock de la dependencia de conexión Odoo
    async def mock_get_odoo_connection():
        return mock_odoo_connection

    # Mock de la dependencia del gateway
    def mock_get_gateway():
        return mock_gateway

    # Aplicar los mocks a las dependencias
    app.dependency_overrides[get_odoo_connection_dependency] = mock_get_odoo_connection
    app.dependency_overrides[get_task_gateway] = mock_get_gateway

    yield

    # Limpiar los mocks después de cada test
    app.dependency_overrides.clear()


class TestGetTasks:
    def test_get_project_tasks_success(self, mock_gateway, test_client):
        # Arrange
        mock_tasks = [
            Task(id=1, name="Tarea 1"),
            Task(id=2, name="Tarea 2"),
        ]
        mock_gateway.all.return_value = mock_tasks

        # Act
        response = test_client.get("/api/v1/projects/1/tasks")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Tarea 1"
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Tarea 2"
        mock_gateway.all.assert_called_once_with(1)

    def test_get_tasks_empty(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        response = test_client.get("/api/v1/projects/1/tasks")

        # Assert
        assert response.status_code == 200
        assert response.json() == []
        mock_gateway.all.assert_called_once_with(1)

    def test_get_tasks_server_error(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all.side_effect = Exception("Error de servidor")

        # Act
        response = test_client.get("/api/v1/projects/1/tasks")

        # Assert
        assert response.status_code == 500
        assert "Error interno del servidor" in response.json()["detail"]
