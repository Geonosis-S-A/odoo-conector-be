from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
import pytest
from unittest.mock import Mock
from app.task.domain.models import Task
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooTaskGateway:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.odoo_client = get_odoo_connection()
        self.gateway = OdooTaskGateway(self.odoo_client)
        yield

    def test_returns_tasks_for_specific_project(self):
        # Arrange
        test_project_id = 2  # ID de proyecto de prueba

        # Act
        tasks = self.gateway.all(test_project_id)

        assert tasks is not None
        # Assert
        assert len(tasks) > 0
        assert all(isinstance(task, Task) for task in tasks)
        assert all(hasattr(task, "id") for task in tasks)
        assert all(hasattr(task, "name") for task in tasks)
        assert all(hasattr(task, "project_id") for task in tasks)
        assert all(hasattr(task, "project_name") for task in tasks)
        assert all(hasattr(task, "subtask") for task in tasks)
        assert all(isinstance(task.id, int) for task in tasks)
        assert all(isinstance(task.name, str) for task in tasks)
        assert all(isinstance(task.project_id, int) for task in tasks)
        assert all(isinstance(task.project_name, str) for task in tasks)


class TestOdooTaskGatewayUnit:
    @pytest.fixture
    def mock_odoo_client(self):
        """Fixture que proporciona un cliente Odoo mockeado."""
        return {
            "models": Mock(),
            "uid": 1,
            "ODOO_DB": "test_db",
            "ODOO_PASSWORD": "test_pass",
        }

    @pytest.fixture
    def gateway(self, mock_odoo_client):
        """Fixture que proporciona un gateway con cliente mockeado."""
        return OdooTaskGateway(mock_odoo_client)

    def test_all_returns_tasks_with_nested_subtasks(self, gateway, mock_odoo_client):
        # Arrange - Simular respuesta de Odoo con tareas jerárquicas
        mock_odoo_response = [
            {
                "id": 1,
                "name": "Tarea Principal",
                "project_id": [10, "Proyecto A"],
                "state": "01_in_progress",
                "child_ids": [2, 3],
                "parent_id": False,
            },
            {
                "id": 2,
                "name": "Subtarea 1",
                "project_id": [10, "Proyecto A"],
                "state": "1_done",
                "child_ids": [4],
                "parent_id": [1, "Tarea Principal"],
            },
            {
                "id": 3,
                "name": "Subtarea 2",
                "project_id": [10, "Proyecto A"],
                "state": "01_in_progress",
                "child_ids": [],
                "parent_id": [1, "Tarea Principal"],
            },
            {
                "id": 4,
                "name": "Sub-subtarea",
                "project_id": [10, "Proyecto A"],
                "state": "01_in_progress",
                "child_ids": [],
                "parent_id": [2, "Subtarea 1"],
            },
        ]

        mock_odoo_client["models"].execute_kw.return_value = mock_odoo_response

        # Act
        result = gateway.all(10)

        # Assert
        assert result is not None
        assert len(result) == 1  # Solo una tarea principal

        # Verificar tarea principal
        main_task = result[0]
        assert isinstance(main_task, Task)
        assert main_task.id == 1
        assert main_task.name == "Tarea Principal"
        assert main_task.project_id == 10
        assert main_task.project_name == "Proyecto A"
        assert main_task.state == "01_in_progress"
        assert len(main_task.subtask) == 2

        # Verificar primera subtarea
        subtask_1 = main_task.subtask[0]
        assert subtask_1.id == 2
        assert subtask_1.name == "Subtarea 1"
        assert subtask_1.state == "1_done"
        assert len(subtask_1.subtask) == 1

        # Verificar sub-subtarea
        sub_subtask = subtask_1.subtask[0]
        assert sub_subtask.id == 4
        assert sub_subtask.name == "Sub-subtarea"
        assert sub_subtask.state == "01_in_progress"
        assert len(sub_subtask.subtask) == 0

        # Verificar segunda subtarea
        subtask_2 = main_task.subtask[1]
        assert subtask_2.id == 3
        assert subtask_2.name == "Subtarea 2"
        assert subtask_2.state == "01_in_progress"
        assert len(subtask_2.subtask) == 0

    def test_all_returns_multiple_main_tasks_with_subtasks(
        self, gateway, mock_odoo_client
    ):
        # Arrange - Múltiples tareas principales con sus subtareas
        mock_odoo_response = [
            {
                "id": 1,
                "name": "Primera Tarea Principal",
                "project_id": [10, "Proyecto A"],
                "state": "01_in_progress",
                "child_ids": [3],
                "parent_id": False,
            },
            {
                "id": 2,
                "name": "Segunda Tarea Principal",
                "project_id": [10, "Proyecto A"],
                "state": "1_done",
                "child_ids": [4, 5],
                "parent_id": False,
            },
            {
                "id": 3,
                "name": "Subtarea de Primera",
                "project_id": [10, "Proyecto A"],
                "state": "01_in_progress",
                "child_ids": [],
                "parent_id": [1, "Primera Tarea Principal"],
            },
            {
                "id": 4,
                "name": "Primera Subtarea de Segunda",
                "project_id": [10, "Proyecto A"],
                "state": "1_done",
                "child_ids": [],
                "parent_id": [2, "Segunda Tarea Principal"],
            },
            {
                "id": 5,
                "name": "Segunda Subtarea de Segunda",
                "project_id": [10, "Proyecto A"],
                "state": "04_waiting_normal",
                "child_ids": [],
                "parent_id": [2, "Segunda Tarea Principal"],
            },
        ]

        mock_odoo_client["models"].execute_kw.return_value = mock_odoo_response

        # Act
        result = gateway.all(10)

        # Assert
        assert result is not None
        assert len(result) == 2  # Dos tareas principales

        # Verificar primera tarea principal
        task_1 = result[0]
        assert task_1.id == 1
        assert task_1.name == "Primera Tarea Principal"
        assert len(task_1.subtask) == 1
        assert task_1.subtask[0].id == 3
        assert task_1.subtask[0].name == "Subtarea de Primera"

        # Verificar segunda tarea principal
        task_2 = result[1]
        assert task_2.id == 2
        assert task_2.name == "Segunda Tarea Principal"
        assert len(task_2.subtask) == 2
        assert task_2.subtask[0].id == 4
        assert task_2.subtask[0].name == "Primera Subtarea de Segunda"
        assert task_2.subtask[0].state == "1_done"
        assert task_2.subtask[1].id == 5
        assert task_2.subtask[1].name == "Segunda Subtarea de Segunda"
        assert task_2.subtask[1].state == "04_waiting_normal"

    def test_all_returns_tasks_without_subtasks(self, gateway, mock_odoo_client):
        # Arrange - Tareas sin subtareas
        mock_odoo_response = [
            {
                "id": 1,
                "name": "Tarea Sin Subtareas 1",
                "project_id": [10, "Proyecto A"],
                "state": "01_in_progress",
                "child_ids": [],
                "parent_id": False,
            },
            {
                "id": 2,
                "name": "Tarea Sin Subtareas 2",
                "project_id": [10, "Proyecto A"],
                "state": "1_done",
                "child_ids": [],
                "parent_id": False,
            },
        ]

        mock_odoo_client["models"].execute_kw.return_value = mock_odoo_response

        # Act
        result = gateway.all(10)

        # Assert
        assert result is not None
        assert len(result) == 2

        # Verificar que ambas tareas no tienen subtareas
        for task in result:
            assert isinstance(task, Task)
            assert len(task.subtask) == 0
            assert task.project_id == 10
            assert task.project_name == "Proyecto A"

    def test_all_returns_none_when_no_tasks_found(self, gateway, mock_odoo_client):
        # Arrange
        mock_odoo_client["models"].execute_kw.return_value = []

        # Act
        result = gateway.all(999)

        # Assert
        assert result is None
