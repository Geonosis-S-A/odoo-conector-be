from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
import pytest
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

        # Debug information
        print(f"\nTareas encontradas para el proyecto {test_project_id}:")
        for task in tasks:
            print(f"ID: {task.id}, Nombre: {task.name}")

        # Assert
        assert len(tasks) > 0
        assert all(isinstance(task, Task) for task in tasks)
        assert all(hasattr(task, "id") for task in tasks)
        assert all(hasattr(task, "name") for task in tasks)
        assert all(isinstance(task.id, int) for task in tasks)
        assert all(isinstance(task.name, str) for task in tasks)
