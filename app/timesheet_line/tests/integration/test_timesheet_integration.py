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
def test_create_and_delete_timesheet_line(test_client):
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
    create_response = test_client.post("/api/v1/timesheet/", json=request_data)
    if create_response.status_code != 200:
        print("create response:", create_response.json())
    # Assert - Crear
    assert create_response.status_code == 200
    created_id = create_response.json()["id"]
    assert isinstance(created_id, int)
    assert created_id > 0

    # Act - Eliminar
    delete_response = test_client.delete(f"/api/v1/timesheet/{created_id}")
    if delete_response.status_code != 200:
        print("Delete response:", delete_response.json())
    # Assert - Eliminar
    assert delete_response.status_code == 200
    assert (
        delete_response.json()["message"]
        == "Línea de timesheet eliminada correctamente"
    )


@pytest.mark.integration
def test_list_timesheet_lines(test_client):
    """Test de integración que prueba el listado de líneas de timesheet."""
    # Act
    response = test_client.get("/api/v1/timesheet/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar la estructura de los datos
    if len(data) > 0:
        assert all(isinstance(item["id"], int) for item in data)
        assert all(isinstance(item["name"], str) for item in data)
        assert all(isinstance(item["employee_id"], int) for item in data)
        # Cambiado: project es un objeto, no un id plano
        assert all(isinstance(item["project"], dict) for item in data)
        assert all(isinstance(item["project"]["id"], int) for item in data)
        assert all(isinstance(item["hours"], (int, float)) for item in data)
        assert all(isinstance(item["date"], str) for item in data)
        # Task puede ser None o un dict
        assert all(
            item["task"] is None or isinstance(item["task"], dict) for item in data
        )


@pytest.mark.integration
def test_create_timesheet_line_validation(test_client):
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
    response = test_client.post("/api/v1/timesheet/", json=request_data)

    # Assert
    assert response.status_code == 400
    assert "Las horas no pueden ser negativas" in response.json()["detail"]


@pytest.mark.integration
def test_edit_timesheet_line(test_client):
    """Test de integración que prueba la edición de una línea de timesheet."""
    # Arrange - Crear una línea inicial
    create_data = {
        "name": "Test Timesheet",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-03-20",
    }
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()["id"]

    # Act - Editar la línea
    edit_data = {
        "id": created_id,
        "name": "Test Timesheet Updated",
        "employee_id": 1,
        "project_id": 1,
        "hours": 4.0,
        "date": "2024-03-20",
    }
    edit_response = test_client.put(f"/api/v1/timesheet/{created_id}", json=edit_data)

    # Assert
    assert edit_response.status_code == 200
    assert edit_response.json()["success"] is True

    # Verificar que los cambios se aplicaron
    get_response = test_client.get("/api/v1/timesheet/")
    assert get_response.status_code == 200
    updated_line = next(
        (line for line in get_response.json() if line["id"] == created_id), None
    )
    assert updated_line is not None
    assert updated_line["name"] == "Test Timesheet Updated"
    assert updated_line["hours"] == 4.0

    # Limpieza
    delete_response = test_client.delete(f"/api/v1/timesheet/{created_id}")
    assert delete_response.status_code == 200


@pytest.mark.integration
def test_edit_timesheet_line_validation(test_client):
    """Test de integración que prueba la validación al editar una línea de timesheet."""
    # Arrange - Crear una línea inicial
    create_data = {
        "name": "Test Timesheet",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-03-20",
    }
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()["id"]

    # Act - Intentar editar con horas negativas
    edit_data = {
        "id": created_id,
        "name": "Test Timesheet Updated",
        "employee_id": 1,
        "project_id": 1,
        "hours": -1.0,  # Horas inválidas
        "date": "2024-03-20",
    }
    edit_response = test_client.put(f"/api/v1/timesheet/{created_id}", json=edit_data)

    # Assert
    assert edit_response.status_code == 400
    assert "Las horas no pueden ser negativas" in edit_response.json()["detail"]

    # Act - Intentar editar con ID incorrecto en la URL
    edit_data["hours"] = 4.0  # Corregimos las horas
    edit_response = test_client.put(
        f"/api/v1/timesheet/{created_id + 1}", json=edit_data
    )

    # Assert
    assert edit_response.status_code == 400
    assert (
        "El ID en la URL no coincide con el ID en el body"
        in edit_response.json()["detail"]
    )

    # Limpieza
    delete_response = test_client.delete(f"/api/v1/timesheet/{created_id}")
    assert delete_response.status_code == 200
