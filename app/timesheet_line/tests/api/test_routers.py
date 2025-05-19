import pytest
from fastapi.testclient import TestClient
from app.timesheet_line.api.routers import router
from fastapi import FastAPI
from app.timesheet_line.infra.external.odoo.get_odoo import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_repository import (
    OdooTimesheetLineRepository,
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_repository():
    odoo_client = get_odoo_connection()
    repository = OdooTimesheetLineRepository(odoo_client)
    yield repository
    # Limpieza después de cada test
    _cleanup_test_data(repository)


def _cleanup_test_data(repository):
    """Limpia los datos de prueba creados durante los tests"""
    test_lines = repository.all()
    for line in test_lines:
        if line.name == "Test Timesheet":
            if line.id:
                repository.delete(line.id)


def test_create_timesheet_line_success():
    # Arrange
    request_data = {
        "name": "Test Timesheet",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-03-20",
        "task_id": 1,
    }

    # Act
    response = client.post("/timesheet/", json=request_data)

    # Assert
    assert response.status_code == 200
    created_id = response.json()
    assert isinstance(created_id, int)
    assert created_id > 0


def test_create_timesheet_line_validation_error():
    # Arrange
    request_data = {
        "name": "Test Timesheet",
        "employee_id": 1,
        "project_id": 1,
        "hours": -1,  # Horas inválidas
        "date": "2024-03-20",
    }

    # Act
    response = client.post("/timesheet/", json=request_data)

    # Assert
    assert response.status_code == 400
    assert "Las horas no pueden ser negativas" in response.json()["detail"]


def test_list_timesheet_lines_success():
    # Act
    response = client.get("/timesheet/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert all(isinstance(item["id"], int) for item in data)
        assert all(isinstance(item["name"], str) for item in data)
        assert all(isinstance(item["employee_id"], int) for item in data)
        assert all(isinstance(item["project_id"], int) for item in data)
        assert all(isinstance(item["hours"], (int, float)) for item in data)
        assert all(isinstance(item["date"], str) for item in data)


def test_delete_timesheet_line_success():
    # Arrange
    # Primero creamos una línea para luego eliminarla
    create_response = client.post(
        "/timesheet/",
        json={
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2024-03-20",
        },
    )
    created_id = create_response.json()

    # Act
    response = client.delete(f"/timesheet/{created_id}")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "Línea de timesheet eliminada correctamente"}


def test_delete_timesheet_line_not_found():
    # Act
    response = client.delete("/timesheet/999999")

    # Assert
    assert response.status_code == 404
    assert "Línea de timesheet no encontrada" in response.json()["detail"]
