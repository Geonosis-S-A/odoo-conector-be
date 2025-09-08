import pytest
from unittest.mock import Mock
from app.task.application.use_cases.obtener_tareas import ObtenerTareasUseCase
from app.task.domain.models import Task
from app.task.domain.gateway import TaskGateway
from app.task.application.Exeptions import (
    TasksNotFound_userId,
    ProjectNotFound,
)


class TestObtenerTareasUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=TaskGateway)

    @pytest.fixture
    def mock_odoo_task_gateway(self):
        return Mock()

    @pytest.fixture
    def mock_odoo_employee_gateway(self):
        return Mock()

    @pytest.fixture
    def use_case(
        self, mock_gateway, mock_odoo_task_gateway, mock_odoo_employee_gateway
    ):
        return ObtenerTareasUseCase(
            mock_gateway, mock_odoo_task_gateway, mock_odoo_employee_gateway
        )

    def test_execute_returns_project_tasks(
        self, use_case, mock_gateway, mock_odoo_task_gateway
    ):
        # Arrange
        test_tasks = [
            Task(
                id=1,
                name="Tarea del Proyecto 1",
                project_id=10,
                project_name="Proyecto A",
                state="01_in_progress",
                subtask=[],
            ),
            Task(
                id=2,
                name="Tarea del Proyecto 2",
                project_id=10,
                project_name="Proyecto A",
                state="01_in_progress",
                subtask=[],
            ),
        ]
        mock_odoo_task_gateway.get_project_by_id.return_value = {
            "id": 1,
            "name": "Proyecto A",
        }
        mock_gateway.all.return_value = test_tasks
        test_project_id = 1

        # Act
        result = use_case.execute(test_project_id)
        assert result is not None

        # Assert
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(
            test_project_id
        )
        mock_gateway.all.assert_called_once_with(test_project_id)
        assert len(result) == 2
        assert all(isinstance(task, Task) for task in result)
        assert result[0].id == 1
        assert result[0].name == "Tarea del Proyecto 1"
        assert result[0].project_id == 10
        assert result[0].project_name == "Proyecto A"
        assert result[0].subtask == []
        assert result[1].id == 2
        assert result[1].name == "Tarea del Proyecto 2"
        assert result[1].project_id == 10
        assert result[1].project_name == "Proyecto A"
        assert result[1].subtask == []

    def test_execute_returns_tasks_with_subtasks(
        self, use_case, mock_gateway, mock_odoo_task_gateway
    ):
        # Arrange - Tarea con subtareas anidadas
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

        test_tasks = [main_task]
        mock_odoo_task_gateway.get_project_by_id.return_value = {
            "id": 1,
            "name": "Proyecto A",
        }
        mock_gateway.all.return_value = test_tasks
        test_project_id = 1

        # Act
        result = use_case.execute(test_project_id)

        # Assert
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(
            test_project_id
        )
        mock_gateway.all.assert_called_once_with(test_project_id)
        assert len(result) == 1
        assert isinstance(result[0], Task)

        # Verificar tarea principal
        main_task_result = result[0]
        assert main_task_result.id == 1
        assert main_task_result.name == "Tarea Principal"
        assert main_task_result.state == "01_in_progress"
        assert len(main_task_result.subtask) == 1

        # Verificar subtarea nivel 1
        subtask_1_result = main_task_result.subtask[0]
        assert subtask_1_result.id == 3
        assert subtask_1_result.name == "Subtarea Nivel 1"
        assert subtask_1_result.state == "01_in_progress"
        assert len(subtask_1_result.subtask) == 1

        # Verificar subtarea nivel 2
        subtask_2_result = subtask_1_result.subtask[0]
        assert subtask_2_result.id == 4
        assert subtask_2_result.name == "Subtarea Nivel 2"
        assert subtask_2_result.state == "1_done"
        assert len(subtask_2_result.subtask) == 0

    def test_execute_returns_multiple_tasks_with_different_subtask_structures(
        self, use_case, mock_gateway, mock_odoo_task_gateway
    ):
        # Arrange - Múltiples tareas con diferentes estructuras de subtareas
        # Tarea 1: Sin subtareas
        task_without_subtasks = Task(
            id=1,
            name="Tarea Sin Subtareas",
            project_id=10,
            project_name="Proyecto A",
            state="1_done",
            subtask=[],
        )

        # Tarea 2: Con una subtarea
        task2_subtask = Task(
            id=3,
            name="Única Subtarea",
            project_id=10,
            project_name="Proyecto A",
            state="01_in_progress",
            subtask=[],
        )

        task_with_one_subtask = Task(
            id=2,
            name="Tarea Con Una Subtarea",
            project_id=10,
            project_name="Proyecto A",
            state="01_in_progress",
            subtask=[task2_subtask],
        )

        # Tarea 3: Con múltiples subtareas
        task3_subtask1 = Task(
            id=4,
            name="Primera Subtarea",
            project_id=10,
            project_name="Proyecto A",
            state="1_done",
            subtask=[],
        )

        task3_subtask2 = Task(
            id=5,
            name="Segunda Subtarea",
            project_id=10,
            project_name="Proyecto A",
            state="04_waiting_normal",
            subtask=[],
        )

        task_with_multiple_subtasks = Task(
            id=6,
            name="Tarea Con Múltiples Subtareas",
            project_id=10,
            project_name="Proyecto A",
            state="01_in_progress",
            subtask=[task3_subtask1, task3_subtask2],
        )

        test_tasks = [
            task_without_subtasks,
            task_with_one_subtask,
            task_with_multiple_subtasks,
        ]
        mock_odoo_task_gateway.get_project_by_id.return_value = {
            "id": 1,
            "name": "Proyecto A",
        }
        mock_gateway.all.return_value = test_tasks
        test_project_id = 1

        # Act
        result = use_case.execute(test_project_id)

        # Assert
        assert len(result) == 3

        # Verificar tarea sin subtareas
        task1_result = result[0]
        assert task1_result.id == 1
        assert task1_result.name == "Tarea Sin Subtareas"
        assert len(task1_result.subtask) == 0

        # Verificar tarea con una subtarea
        task2_result = result[1]
        assert task2_result.id == 2
        assert task2_result.name == "Tarea Con Una Subtarea"
        assert len(task2_result.subtask) == 1
        assert task2_result.subtask[0].id == 3
        assert task2_result.subtask[0].name == "Única Subtarea"

        # Verificar tarea con múltiples subtareas
        task3_result = result[2]
        assert task3_result.id == 6
        assert task3_result.name == "Tarea Con Múltiples Subtareas"
        assert len(task3_result.subtask) == 2
        assert task3_result.subtask[0].id == 4
        assert task3_result.subtask[0].name == "Primera Subtarea"
        assert task3_result.subtask[0].state == "1_done"
        assert task3_result.subtask[1].id == 5
        assert task3_result.subtask[1].name == "Segunda Subtarea"
        assert task3_result.subtask[1].state == "04_waiting_normal"

    def test_execute_raises_project_not_found_when_project_does_not_exist(
        self, use_case, mock_gateway, mock_odoo_task_gateway
    ):
        # Arrange
        test_project_id = 999
        mock_odoo_task_gateway.get_project_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ProjectNotFound):
            use_case.execute(test_project_id)

        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(
            test_project_id
        )
        mock_gateway.all.assert_not_called()

    def test_execute_returns_empty_list_when_project_has_no_tasks(
        self, use_case, mock_gateway, mock_odoo_task_gateway
    ):
        # Arrange
        test_project_id = 1
        mock_odoo_task_gateway.get_project_by_id.return_value = {
            "id": 1,
            "name": "Proyecto A",
        }
        mock_gateway.all.return_value = []

        # Act
        result = use_case.execute(test_project_id)

        # Assert
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(
            test_project_id
        )
        mock_gateway.all.assert_called_once_with(test_project_id)
        assert result == []
        assert len(result) == 0

    def test_execute_returns_empty_list_when_gateway_returns_none(
        self, use_case, mock_gateway, mock_odoo_task_gateway
    ):
        # Arrange
        test_project_id = 1
        mock_odoo_task_gateway.get_project_by_id.return_value = {
            "id": 1,
            "name": "Proyecto A",
        }
        mock_gateway.all.return_value = None

        # Act
        result = use_case.execute(test_project_id)

        # Assert
        mock_odoo_task_gateway.get_project_by_id.assert_called_once_with(
            test_project_id
        )
        mock_gateway.all.assert_called_once_with(test_project_id)
        assert result == []
        assert len(result) == 0
