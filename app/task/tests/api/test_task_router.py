import pytest
from unittest.mock import Mock
from app.task.api.routers import get_task_gateway, get_employee_gateway
from app.task.domain.models import Task
from app.task.domain.gateway import TaskGateway
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection_dependency
from app.project.domain.models import Project


@pytest.fixture
def mock_gateway():
    """Fixture que proporciona un gateway mockeado."""
    return Mock(spec=TaskGateway)


@pytest.fixture
def mock_odoo_task_gateway():
    """Fixture que proporciona un OdooTaskGateway mockeado."""
    return Mock(spec=OdooTaskGateway)


@pytest.fixture
def mock_employee_gateway():
    """Fixture que proporciona un employee gateway mockeado."""
    return Mock(spec=OdooEmployeeGateway)


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
def setup_dependencies(
    mock_odoo_connection, mock_gateway, mock_odoo_task_gateway, mock_employee_gateway
):
    """Fixture que configura las dependencias para todos los tests."""
    from app.main import app

    # Mock de la dependencia de conexión Odoo
    async def mock_get_odoo_connection():
        return mock_odoo_connection

    # Mock de la dependencia del gateway - retorna el mock_odoo_task_gateway
    def mock_get_gateway():
        return mock_odoo_task_gateway

    # Mock de la dependencia del employee gateway
    def mock_get_employee_gateway():
        return mock_employee_gateway

    # Aplicar los mocks a las dependencias
    app.dependency_overrides[get_odoo_connection_dependency] = mock_get_odoo_connection
    app.dependency_overrides[get_task_gateway] = mock_get_gateway
    app.dependency_overrides[get_employee_gateway] = mock_get_employee_gateway

    yield

    # Limpiar los mocks después de cada test
    app.dependency_overrides.clear()


class TestGetTasks:
    def test_get_project_tasks_success(
        self, mock_odoo_task_gateway, mock_employee_gateway, test_client
    ):
        # Arrange
        mock_tasks = [
            Task(
                id=1,
                name="Tarea 1",
                project_id=10,
                project_name="Proyecto A",
                state="01_in_progress",
                subtask=[],
            ),
            Task(
                id=2,
                name="Tarea 2",
                project_id=10,
                project_name="Proyecto A",
                state="01_in_progress",
                subtask=[],
            ),
        ]
        mock_project = Project(id=1, name="Proyecto A")
        mock_odoo_task_gateway.get_project_by_id.return_value = mock_project
        mock_odoo_task_gateway.all.return_value = mock_tasks

        # Act
        response = test_client.get("/api/v1/tasks/?project_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Tarea 1"
        assert data[0]["project_id"] == 10
        assert data[0]["project_name"] == "Proyecto A"
        assert data[0]["state"] == "01_in_progress"
        assert data[0]["subtask"] == []
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Tarea 2"
        assert data[1]["project_id"] == 10
        assert data[1]["project_name"] == "Proyecto A"
        assert data[1]["state"] == "01_in_progress"
        assert data[1]["subtask"] == []
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(1)
        mock_odoo_task_gateway.all.assert_called_once_with(1)

    def test_get_project_tasks_with_subtasks_success(
        self, mock_odoo_task_gateway, mock_employee_gateway, test_client
    ):
        # Arrange - Tarea principal con subtareas anidadas
        subtask_level_2 = Task(
            id=4,
            name="Subtarea Nivel 2",
            project_id=10,
            project_name="Proyecto A",
            state="1_done",
            subtask=[],
        )

        subtask_level_1 = Task(
            id=3,
            name="Subtarea Nivel 1",
            project_id=10,
            project_name="Proyecto A",
            state="01_in_progress",
            subtask=[subtask_level_2],
        )

        main_task = Task(
            id=1,
            name="Tarea Principal",
            project_id=10,
            project_name="Proyecto A",
            state="01_in_progress",
            subtask=[subtask_level_1],
        )

        mock_tasks = [main_task]
        mock_project = Project(id=1, name="Proyecto A")
        mock_odoo_task_gateway.get_project_by_id.return_value = mock_project
        mock_odoo_task_gateway.all.return_value = mock_tasks

        # Act
        response = test_client.get("/api/v1/tasks/?project_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        # Verificar tarea principal
        main_task_data = data[0]
        assert main_task_data["id"] == 1
        assert main_task_data["name"] == "Tarea Principal"
        assert main_task_data["state"] == "01_in_progress"
        assert len(main_task_data["subtask"]) == 1

        # Verificar subtarea nivel 1
        subtask_1_data = main_task_data["subtask"][0]
        assert subtask_1_data["id"] == 3
        assert subtask_1_data["name"] == "Subtarea Nivel 1"
        assert subtask_1_data["state"] == "01_in_progress"
        assert len(subtask_1_data["subtask"]) == 1

        # Verificar subtarea nivel 2
        subtask_2_data = subtask_1_data["subtask"][0]
        assert subtask_2_data["id"] == 4
        assert subtask_2_data["name"] == "Subtarea Nivel 2"
        assert subtask_2_data["state"] == "1_done"
        assert len(subtask_2_data["subtask"]) == 0

        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(1)
        mock_odoo_task_gateway.all.assert_called_once_with(1)

    def test_get_project_tasks_multiple_main_tasks_with_subtasks(
        self, mock_odoo_task_gateway, mock_employee_gateway, test_client
    ):
        # Arrange - Múltiples tareas principales, cada una con subtareas
        task1_subtask = Task(
            id=3,
            name="Subtarea de Tarea 1",
            project_id=10,
            project_name="Proyecto A",
            state="1_done",
            subtask=[],
        )

        task2_subtask1 = Task(
            id=5,
            name="Subtarea 1 de Tarea 2",
            project_id=10,
            project_name="Proyecto A",
            state="01_in_progress",
            subtask=[],
        )

        task2_subtask2 = Task(
            id=6,
            name="Subtarea 2 de Tarea 2",
            project_id=10,
            project_name="Proyecto A",
            state="04_waiting_normal",
            subtask=[],
        )

        mock_tasks = [
            Task(
                id=1,
                name="Tarea Principal 1",
                project_id=10,
                project_name="Proyecto A",
                state="01_in_progress",
                subtask=[task1_subtask],
            ),
            Task(
                id=2,
                name="Tarea Principal 2",
                project_id=10,
                project_name="Proyecto A",
                state="01_in_progress",
                subtask=[task2_subtask1, task2_subtask2],
            ),
        ]

        mock_project = Project(id=1, name="Proyecto A")
        mock_odoo_task_gateway.get_project_by_id.return_value = mock_project
        mock_odoo_task_gateway.all.return_value = mock_tasks

        # Act
        response = test_client.get("/api/v1/tasks/?project_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Verificar primera tarea principal y su subtarea
        task1_data = data[0]
        assert task1_data["id"] == 1
        assert task1_data["name"] == "Tarea Principal 1"
        assert len(task1_data["subtask"]) == 1
        assert task1_data["subtask"][0]["id"] == 3
        assert task1_data["subtask"][0]["name"] == "Subtarea de Tarea 1"
        assert task1_data["subtask"][0]["state"] == "1_done"

        # Verificar segunda tarea principal y sus subtareas
        task2_data = data[1]
        assert task2_data["id"] == 2
        assert task2_data["name"] == "Tarea Principal 2"
        assert len(task2_data["subtask"]) == 2
        assert task2_data["subtask"][0]["id"] == 5
        assert task2_data["subtask"][0]["name"] == "Subtarea 1 de Tarea 2"
        assert task2_data["subtask"][0]["state"] == "01_in_progress"
        assert task2_data["subtask"][1]["id"] == 6
        assert task2_data["subtask"][1]["name"] == "Subtarea 2 de Tarea 2"
        assert task2_data["subtask"][1]["state"] == "04_waiting_normal"

    def test_get_tasks_empty_returns_empty_array(
        self, mock_odoo_task_gateway, test_client
    ):
        # Arrange
        mock_project = Project(id=1, name="Proyecto A")
        mock_odoo_task_gateway.get_project_by_id.return_value = mock_project
        mock_odoo_task_gateway.all.return_value = None

        # Act
        response = test_client.get("/api/v1/tasks/?project_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert len(data) == 0
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(1)
        mock_odoo_task_gateway.all.assert_called_once_with(1)

    def test_get_tasks_no_tasks_for_project_returns_empty_array(
        self, mock_odoo_task_gateway, test_client
    ):
        # Arrange
        mock_project = Project(id=1, name="Proyecto A")
        mock_odoo_task_gateway.get_project_by_id.return_value = mock_project
        mock_odoo_task_gateway.all.return_value = []

        # Act
        response = test_client.get("/api/v1/tasks/?project_id=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert len(data) == 0
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(1)
        mock_odoo_task_gateway.all.assert_called_once_with(1)

    def test_get_tasks_project_not_found(self, mock_odoo_task_gateway, test_client):
        # Arrange
        mock_odoo_task_gateway.get_project_by_id.return_value = None

        # Act
        response = test_client.get("/api/v1/tasks/?project_id=999")

        # Assert
        assert response.status_code == 404
        assert "Proyecto con el id 999 no encontrado" in response.json()["detail"]


    def test_get_tasks_invalid_project_id(self, test_client):
        # Act
        response = test_client.get("/api/v1/tasks/?project_id=invalid")

        # Assert
        assert (
            response.status_code == 422
        )  # Unprocessable Entity para parámetros inválidos
