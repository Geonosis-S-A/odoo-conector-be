import pytest
from unittest.mock import Mock
from app.task.api.routers import get_task_gateway
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
            Task(id=1, name="Tarea 1", project_id=10, project_name="Proyecto A"),
            Task(id=2, name="Tarea 2", project_id=10, project_name="Proyecto A"),
        ]
        mock_gateway.all.return_value = mock_tasks

        # Act
        response = test_client.get("/api/v1/tasks/projects/1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Tarea 1"
        assert data[0]["project_id"] == 10
        assert data[0]["project_name"] == "Proyecto A"
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Tarea 2"
        assert data[1]["project_id"] == 10
        assert data[1]["project_name"] == "Proyecto A"
        mock_gateway.all.assert_called_once_with(1)

    def test_get_tasks_empty(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        response = test_client.get("/api/v1/tasks/projects/1")

        # Assert
        assert response.status_code == 200
        assert response.json() == []
        mock_gateway.all.assert_called_once_with(1)

    def test_get_tasks_server_error(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all.side_effect = Exception("Error de servidor")

        # Act
        response = test_client.get("/api/v1/tasks/projects/1")

        # Assert
        assert response.status_code == 500
        assert "Error interno del servidor" in response.json()["detail"]


class TestGetTasksByUser:
    def test_get_user_tasks_success(self, mock_gateway, test_client):
        # Arrange
        mock_tasks = [
            Task(id=1, name="Mi Tarea 1", project_id=20, project_name="Proyecto B"),
            Task(id=2, name="Mi Tarea 2", project_id=30, project_name="Proyecto C"),
        ]
        mock_gateway.all_by_user.return_value = mock_tasks

        # Act
        response = test_client.get("/api/v1/tasks/?user_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Mi Tarea 1"
        assert data[0]["project_id"] == 20
        assert data[0]["project_name"] == "Proyecto B"
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Mi Tarea 2"
        assert data[1]["project_id"] == 30
        assert data[1]["project_name"] == "Proyecto C"
        # Verificar que se llamó con el user_id del usuario autenticado (mock user_id = 1)
        mock_gateway.all_by_user.assert_called_once_with(1)

    def test_get_user_tasks_empty(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all_by_user.return_value = []

        # Act
        response = test_client.get("/api/v1/tasks/?user_id=1")

        # Assert
        assert response.status_code == 200
        assert response.json() == []
        mock_gateway.all_by_user.assert_called_once_with(1)

    def test_get_user_tasks_server_error(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all_by_user.side_effect = Exception("Error de servidor")

        # Act
        response = test_client.get("/api/v1/tasks/?user_id=1")

        # Assert
        assert response.status_code == 500
        assert (
            "Error interno del servidor al obtener las tareas del usuario"
            in response.json()["detail"]
        )
