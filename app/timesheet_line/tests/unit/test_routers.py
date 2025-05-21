import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from datetime import date
from app.project.domain.models import Project
from app.task.domain.models import Task
from app.timesheet_line.api.routers import (
    router,
    get_timesheet_gateway,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection_dependency
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def mock_gateway():
    """Fixture que proporciona un repositorio mockeado."""
    return Mock(spec=TimesheetLineGateway)


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

    # Mock de la dependencia de conexión Odoo
    async def mock_get_odoo_connection():
        return mock_odoo_connection

    # Mock de la dependencia del repositorio
    def mock_get_repository():
        return mock_gateway

    # Aplicar los mocks a las dependencias
    app.dependency_overrides[get_odoo_connection_dependency] = mock_get_odoo_connection
    app.dependency_overrides[get_timesheet_gateway] = mock_get_repository

    yield

    # Limpiar los mocks después de cada test
    app.dependency_overrides.clear()


class TestCreateTimesheetLine:
    def test_create_timesheet_line_success(self, mock_gateway):
        # Arrange
        request_data = {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2024-03-20",
            "task_id": 1,
        }
        mock_gateway.create.return_value = 123  # ID simulado

        # Mockeamos también get_by_id para que devuelva el objeto esperado
        mock_gateway.get_by_id.return_value = DetailedTimesheetLine(
            id=123,
            name="Test Timesheet",
            employee_id=1,
            project=Project(id=1, name="Project 1"),
            task=Task(id=1, name="Task 1"),
            hours=8.0,
            date=date(2024, 3, 20),
        )

        # Act
        response = client.post("/timesheet/", json=request_data)

        # Assert
        assert response.status_code == 200
        assert response.json() == {"id": 123}
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_id.assert_called_once_with(123)


class TestListTimesheetLines:
    def test_list_timesheet_lines_success(self, mock_gateway):
        # Arrange
        mock_timesheets = [
            DetailedTimesheetLine(
                id=1,
                name="Test 1",
                employee_id=1,
                project=Project(id=1, name="Project 1"),
                task=Task(id=1, name="Task 1"),
                hours=8.0,
                date=date(2024, 3, 20),
            ),
            DetailedTimesheetLine(
                id=2,
                name="Test 2",
                employee_id=2,
                project=Project(id=2, name="Project 2"),
                task=None,
                hours=4.0,
                date=date(2024, 3, 21),
            ),
        ]
        mock_gateway.all.return_value = mock_timesheets

        # Act
        response = client.get("/timesheet/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["project"]["id"] == 1
        assert data[0]["project"]["name"] == "Project 1"
        assert data[0]["task"]["id"] == 1
        assert data[0]["task"]["name"] == "Task 1"
        assert data[1]["id"] == 2
        assert data[1]["project"]["id"] == 2
        assert data[1]["task"] is None
        mock_gateway.all.assert_called_once()

    def test_list_timesheet_lines_empty(self, mock_gateway):
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        response = client.get("/timesheet/")

        # Assert
        assert response.status_code == 200
        assert response.json() == []
        mock_gateway.all.assert_called_once()

    def test_list_timesheet_lines_server_error(self, mock_gateway):
        # Arrange
        mock_gateway.all.side_effect = Exception("Error de servidor")

        # Act
        response = client.get("/timesheet/")

        # Assert
        assert response.status_code == 500
        assert "Error interno del servidor" in response.json()["detail"]


class TestDeleteTimesheetLine:
    def test_delete_timesheet_line_success(self, mock_gateway):
        # Arrange
        mock_gateway.delete.return_value = True

        # Act
        response = client.delete("/timesheet/123")

        # Assert
        assert response.status_code == 200
        assert response.json() == {
            "message": "Línea de timesheet eliminada correctamente"
        }
        mock_gateway.delete.assert_called_once_with(123)

    def test_delete_timesheet_line_not_found(self, mock_gateway):
        # Arrange
        mock_gateway.delete.return_value = False

        # Act
        response = client.delete("/timesheet/999")

        # Assert
        assert response.status_code == 404
        assert "Línea de timesheet no encontrada" in response.json()["detail"]
        mock_gateway.delete.assert_called_once_with(999)

    def test_delete_timesheet_line_server_error(self, mock_gateway):
        # Arrange
        mock_gateway.delete.side_effect = Exception("Error de servidor")

        # Act
        response = client.delete("/timesheet/123")

        # Assert
        assert response.status_code == 500
        assert "Error interno del servidor" in response.json()["detail"]
