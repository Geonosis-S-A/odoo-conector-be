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
        if "Test Timesheet" in line.name:
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


@pytest.mark.integration
def test_list_timesheet_lines_with_employee_filter(test_client):
    """Test de integración que prueba el filtrado por empleado."""
    # Arrange - Crear una línea de timesheet
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

    # Act - Filtrar por empleado
    response_with_filter = test_client.get("/api/v1/timesheet/?employee_id=1")
    response_without_filter = test_client.get("/api/v1/timesheet/?employee_id=999")

    # Assert
    assert response_with_filter.status_code == 200
    assert response_without_filter.status_code == 200

    data_with_filter = response_with_filter.json()
    data_without_filter = response_without_filter.json()

    # Verificar que el timesheet creado aparece en el filtro correcto
    assert any(item["id"] == created_id for item in data_with_filter)
    assert not any(item["id"] == created_id for item in data_without_filter)

    # Verificar que todos los resultados filtrados son del empleado correcto
    assert all(item["employee_id"] == 1 for item in data_with_filter)

    # Limpieza
    delete_response = test_client.delete(f"/api/v1/timesheet/{created_id}")
    assert delete_response.status_code == 200


@pytest.mark.integration
def test_list_timesheet_lines_with_date_filter(test_client):
    """Test de integración que prueba el filtrado por rango de fechas."""
    # Arrange - Crear líneas de timesheet en diferentes fechas
    create_data_1 = {
        "name": "Test Timesheet 1",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-15",
    }
    create_data_2 = {
        "name": "Test Timesheet 2",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-20",
    }
    create_data_3 = {
        "name": "Test Timesheet 3",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-25",
    }

    create_response_1 = test_client.post("/api/v1/timesheet/", json=create_data_1)
    create_response_2 = test_client.post("/api/v1/timesheet/", json=create_data_2)
    create_response_3 = test_client.post("/api/v1/timesheet/", json=create_data_3)

    assert create_response_1.status_code == 200
    assert create_response_2.status_code == 200
    assert create_response_3.status_code == 200

    created_id_1 = create_response_1.json()["id"]
    created_id_2 = create_response_2.json()["id"]
    created_id_3 = create_response_3.json()["id"]

    # Act - Filtrar por rango de fechas que incluye solo las dos primeras
    response = test_client.get(
        "/api/v1/timesheet/?date_from=2024-01-14&date_to=2024-01-22"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Verificar que solo aparecen las líneas en el rango
    created_ids_in_response = [
        item["id"]
        for item in data
        if item["id"] in [created_id_1, created_id_2, created_id_3]
    ]
    assert created_id_1 in created_ids_in_response
    assert created_id_2 in created_ids_in_response
    assert created_id_3 not in created_ids_in_response

    # Limpieza
    test_client.delete(f"/api/v1/timesheet/{created_id_1}")
    test_client.delete(f"/api/v1/timesheet/{created_id_2}")
    test_client.delete(f"/api/v1/timesheet/{created_id_3}")


@pytest.mark.integration
def test_list_timesheet_lines_with_date_from_filter(test_client):
    """Test de integración que prueba el filtrado solo con fecha de inicio."""
    # Arrange
    create_data_old = {
        "name": "Test Timesheet Old",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-10",
    }
    create_data_new = {
        "name": "Test Timesheet New",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-20",
    }

    create_response_old = test_client.post("/api/v1/timesheet/", json=create_data_old)
    create_response_new = test_client.post("/api/v1/timesheet/", json=create_data_new)

    assert create_response_old.status_code == 200
    assert create_response_new.status_code == 200

    created_id_old = create_response_old.json()["id"]
    created_id_new = create_response_new.json()["id"]

    # Act
    response = test_client.get("/api/v1/timesheet/?date_from=2024-01-15")

    # Assert
    assert response.status_code == 200
    data = response.json()

    created_ids_in_response = [
        item["id"] for item in data if item["id"] in [created_id_old, created_id_new]
    ]
    assert created_id_old not in created_ids_in_response
    assert created_id_new in created_ids_in_response

    # Limpieza
    test_client.delete(f"/api/v1/timesheet/{created_id_old}")
    test_client.delete(f"/api/v1/timesheet/{created_id_new}")


@pytest.mark.integration
def test_list_timesheet_lines_with_date_to_filter(test_client):
    """Test de integración que prueba el filtrado solo con fecha de fin."""
    # Arrange
    create_data_old = {
        "name": "Test Timesheet Old",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-10",
    }
    create_data_new = {
        "name": "Test Timesheet New",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-20",
    }

    create_response_old = test_client.post("/api/v1/timesheet/", json=create_data_old)
    create_response_new = test_client.post("/api/v1/timesheet/", json=create_data_new)

    assert create_response_old.status_code == 200
    assert create_response_new.status_code == 200

    created_id_old = create_response_old.json()["id"]
    created_id_new = create_response_new.json()["id"]

    # Act
    response = test_client.get("/api/v1/timesheet/?date_to=2024-01-15")

    # Assert
    assert response.status_code == 200
    data = response.json()

    created_ids_in_response = [
        item["id"] for item in data if item["id"] in [created_id_old, created_id_new]
    ]
    assert created_id_old in created_ids_in_response
    assert created_id_new not in created_ids_in_response

    # Limpieza
    test_client.delete(f"/api/v1/timesheet/{created_id_old}")
    test_client.delete(f"/api/v1/timesheet/{created_id_new}")


@pytest.mark.integration
def test_list_timesheet_lines_with_combined_filters(test_client):
    """Test de integración que prueba el filtrado combinado por empleado y fechas."""
    # Arrange
    create_data_emp1 = {
        "name": "Test Timesheet Emp1",
        "employee_id": 1,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-15",
    }
    create_data_emp2 = {
        "name": "Test Timesheet Emp2",
        "employee_id": 2,
        "project_id": 1,
        "hours": 8.0,
        "date": "2024-01-15",
    }

    create_response_emp1 = test_client.post("/api/v1/timesheet/", json=create_data_emp1)
    create_response_emp2 = test_client.post("/api/v1/timesheet/", json=create_data_emp2)

    assert create_response_emp1.status_code == 200
    assert create_response_emp2.status_code == 200

    created_id_emp1 = create_response_emp1.json()["id"]
    created_id_emp2 = create_response_emp2.json()["id"]

    # Act
    response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2024-01-14&date_to=2024-01-16"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()

    created_ids_in_response = [
        item["id"] for item in data if item["id"] in [created_id_emp1, created_id_emp2]
    ]
    assert created_id_emp1 in created_ids_in_response
    assert created_id_emp2 not in created_ids_in_response

    # Verificar que todos los resultados son del empleado correcto
    assert all(
        item["employee_id"] == 1
        for item in data
        if item["id"] in created_ids_in_response
    )

    # Limpieza
    test_client.delete(f"/api/v1/timesheet/{created_id_emp1}")
    test_client.delete(f"/api/v1/timesheet/{created_id_emp2}")
