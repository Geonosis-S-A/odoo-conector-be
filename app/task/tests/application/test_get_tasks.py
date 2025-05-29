import pytest
from unittest.mock import Mock
from app.task.application.use_cases.obtener_tareas import ObtenerTareasUseCase
from app.task.domain.models import Task
from app.task.domain.gateway import TaskGateway
from app.task.application.Exeptions import TasksNotFound_userId, ProjectNotFound, TasksNotFound_projectId


class TestObtenerTareasUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=TaskGateway)

    @pytest.fixture
    def mock_odoo_task_gateway(self):
        return Mock()

    @pytest.fixture
    def use_case(self, mock_gateway, mock_odoo_task_gateway):
        return ObtenerTareasUseCase(mock_gateway, mock_odoo_task_gateway)

    def test_execute_returns_project_tasks(self, use_case, mock_gateway, mock_odoo_task_gateway):
        # Arrange
        test_tasks = [
            Task(
                id=1,
                name="Tarea del Proyecto 1",
                project_id=10,
                project_name="Proyecto A",
            ),
            Task(
                id=2,
                name="Tarea del Proyecto 2",
                project_id=10,
                project_name="Proyecto A",
            ),
        ]
        mock_odoo_task_gateway.get_project_by_id.return_value = {"id": 1, "name": "Proyecto A"}
        mock_gateway.all.return_value = test_tasks
        test_project_id = 1

        # Act
        result = use_case.execute(test_project_id)
        # Debug information
        print(f"\nTareas encontradas para el proyecto {test_project_id}:")
        for task in result:
            print(f"ID: {task.id}, Nombre: {task.name}, Proyecto: {task.project_name}")

        # Assert
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(test_project_id)
        mock_gateway.all.assert_called_once_with(test_project_id)
        assert len(result) == 2
        assert all(isinstance(task, Task) for task in result)
        assert result[0].id == 1
        assert result[0].name == "Tarea del Proyecto 1"
        assert result[0].project_id == 10
        assert result[0].project_name == "Proyecto A"
        assert result[1].id == 2
        assert result[1].name == "Tarea del Proyecto 2"
        assert result[1].project_id == 10
        assert result[1].project_name == "Proyecto A"

    def test_execute_raises_project_not_found_when_project_does_not_exist(self, use_case, mock_gateway, mock_odoo_task_gateway):
        # Arrange
        test_project_id = 999
        mock_odoo_task_gateway.get_project_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ProjectNotFound):
            use_case.execute(test_project_id)
        
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(test_project_id)
        mock_gateway.all.assert_not_called()

    def test_execute_raises_tasks_not_found_when_project_has_no_tasks(self, use_case, mock_gateway, mock_odoo_task_gateway):
        # Arrange
        test_project_id = 1
        mock_odoo_task_gateway.get_project_by_id.return_value = {"id": 1, "name": "Proyecto A"}
        mock_gateway.all.return_value = []

        # Act & Assert
        with pytest.raises(TasksNotFound_projectId):
            use_case.execute(test_project_id)
        
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(test_project_id)
        mock_gateway.all.assert_called_once_with(test_project_id)

    def test_execute_by_user_returns_user_tasks(self, use_case, mock_gateway):
        # Arrange
        test_tasks = [
            Task(
                id=3,
                name="Tarea del Usuario 1",
                project_id=20,
                project_name="Proyecto B",
            ),
            Task(
                id=4,
                name="Tarea del Usuario 2",
                project_id=30,
                project_name="Proyecto C",
            ),
        ]
        mock_gateway.all_by_user.return_value = test_tasks
        test_user_id = 5

        # Act
        result = use_case.execute_by_user(test_user_id)
        # Debug information
        print(f"\nTareas encontradas para el usuario {test_user_id}:")
        for task in result:
            print(f"ID: {task.id}, Nombre: {task.name}, Proyecto: {task.project_name}")

        # Assert
        mock_gateway.all_by_user.assert_called_once_with(test_user_id)
        assert len(result) == 2
        assert all(isinstance(task, Task) for task in result)
        assert result[0].id == 3
        assert result[0].name == "Tarea del Usuario 1"
        assert result[0].project_id == 20
        assert result[0].project_name == "Proyecto B"
        assert result[1].id == 4
        assert result[1].name == "Tarea del Usuario 2"
        assert result[1].project_id == 30
        assert result[1].project_name == "Proyecto C"

    def test_execute_by_user_raises_exception_when_no_tasks(
        self, use_case, mock_gateway
    ):
        # Arrange
        mock_gateway.all_by_user.return_value = []
        test_user_id = 10

        # Act & Assert
        with pytest.raises(TasksNotFound_userId):
            use_case.execute_by_user(test_user_id)
        
        mock_gateway.all_by_user.assert_called_once_with(test_user_id)
