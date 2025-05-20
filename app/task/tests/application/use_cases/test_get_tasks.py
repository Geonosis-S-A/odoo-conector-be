import pytest
from unittest.mock import Mock
from app.task.application.use_cases.obtener_tareas import ObtenerTareasUseCase
from app.task.domain.models import Task
from app.task.domain.gateway import TaskGateway


class TestObtenerTareasUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=TaskGateway)

    @pytest.fixture
    def use_case(self, mock_gateway):
        return ObtenerTareasUseCase(mock_gateway)

    def test_execute_returns_project_tasks(self, use_case, mock_gateway):
        # Arrange
        test_tasks = [
            Task(id=1, name="Tarea del Proyecto 1"),
            Task(id=2, name="Tarea del Proyecto 2"),
        ]
        mock_gateway.all.return_value = test_tasks
        test_project_id = 1

        # Act
        result = use_case.execute(test_project_id)
        # Debug information
        print(f"\nTareas encontradas para el proyecto {test_project_id}:")
        for task in result:
            print(f"ID: {task.id}, Nombre: {task.name}")

        # Assert
        mock_gateway.all.assert_called_once_with(test_project_id)
        assert len(result) == 2
        assert all(isinstance(task, Task) for task in result)
        assert result[0].id == 1
        assert result[0].name == "Tarea del Proyecto 1"
        assert result[1].id == 2
        assert result[1].name == "Tarea del Proyecto 2"
