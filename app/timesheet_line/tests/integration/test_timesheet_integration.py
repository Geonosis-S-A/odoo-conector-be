import pytest
from fastapi.testclient import TestClient
from app.timesheet_line.api.routers import router
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_repository():
    """Fixture que configura el repositorio real de Odoo."""
    odoo_client = get_odoo_connection()
    repository = OdooTimesheetLineGateway(odoo_client)
    yield repository
    # Limpieza después de cada test
    _cleanup_test_data(repository)


def _cleanup_test_data(repository):
    """Limpia los datos de prueba creados durante los tests."""
    test_lines = repository.all()
    for line in test_lines:
        if line.name == "Test Timesheet":
            if line.id:
                repository.delete(line.id)


@pytest.mark.integration
def test_create_and_delete_timesheet_line():
    """Test de integración que prueba la creación y eliminación de una línea de timesheet."""
    # Arrange
    request_data = {
        "name": "Test Timesheet",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-03-20",
    }

    # Act - Crear
    create_response = client.post("/timesheet/", json=request_data)

    # Assert - Crear
    assert create_response.status_code == 200
    created_id = create_response.json()["id"]
    assert isinstance(created_id, int)
    assert created_id > 0

    # Act - Eliminar
    delete_response = client.delete(f"/timesheet/{created_id}")

    # Assert - Eliminar
    assert delete_response.status_code == 200
    assert (
        delete_response.json()["message"]
        == "Línea de timesheet eliminada correctamente"
    )


@pytest.mark.integration
def test_list_timesheet_lines():
    """Test de integración que prueba el listado de líneas de timesheet."""
    # Act
    response = client.get("/timesheet/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar la estructura de los datos
    if len(data) > 0:
        assert all(isinstance(item["id"], int) for item in data)
        assert all(isinstance(item["name"], str) for item in data)
        assert all(isinstance(item["employee_id"], int) for item in data)
        assert all(isinstance(item["project_id"], int) for item in data)
        assert all(isinstance(item["hours"], (int, float)) for item in data)
        assert all(isinstance(item["date"], str) for item in data)


@pytest.mark.integration
def test_create_timesheet_line_validation():
    """Test de integración que prueba la validación de datos."""
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
