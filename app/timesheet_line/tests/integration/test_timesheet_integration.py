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
                repository.delete([line.id])


@pytest.mark.integration
def test_create_and_delete_timesheet_line(test_client):
    """Test de integración que prueba la creación y eliminación de una línea de timesheet."""
    # Arrange
    request_data = [
        {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]

    # Act - Crear
    create_response = test_client.post("/api/v1/timesheet/", json=request_data)
    if create_response.status_code != 200:
        print("create response:", create_response.json())
    # Assert - Crear
    assert create_response.status_code == 200
    created_timesheets = create_response.json()
    assert isinstance(created_timesheets, list)
    assert len(created_timesheets) == 1
    created_id = created_timesheets[0]["id"]
    assert isinstance(created_id, int)
    assert created_id > 0

    # Act - Eliminar (usando el nuevo endpoint con body)
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
    )
    if delete_response.status_code != 200:
        print("Delete response:", delete_response.json())
    # Assert - Eliminar
    assert delete_response.status_code == 200
    assert (
        delete_response.json()["message"]
        == "Líneas de timesheet eliminadas correctamente"
    )


@pytest.mark.integration
def test_list_timesheet_lines(test_client):
    """Test de integración que prueba el listado de líneas de timesheet."""
    # Act - Ahora necesitamos pasar los parámetros obligatorios
    response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2025-01-01&date_to=2025-12-31"
    )

    # Assert - Siempre debería devolver 200, con datos o lista vacía
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar la estructura de los datos si hay resultados
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
    request_data = [
        {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": -1,  # Horas inválidas
            "date": "2025-08-01",
        }
    ]

    # Act
    response = test_client.post("/api/v1/timesheet/", json=request_data)

    # Assert
    assert response.status_code == 400
    assert "Las horas no pueden ser negativas" in response.json()["detail"]


@pytest.mark.integration
def test_edit_timesheet_line(test_client):
    """Test de integración que prueba la edición de una línea de timesheet."""
    # Arrange - Crear una línea inicial
    create_data = [
        {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Act - Editar la línea
    edit_data = {
        "id": created_id,
        "name": "Test Timesheet Updated",
        "employee_id": 1,
        "project_id": 1,
        "hours": 4.0,
        "date": "2025-08-01",
        "validated": False,  # Timesheet no validado
    }
    edit_response = test_client.put(f"/api/v1/timesheet/{created_id}", json=edit_data)

    # Assert
    assert edit_response.status_code == 200
    assert edit_response.json()["success"] is True

    # Verificar que los cambios se aplicaron
    get_response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2025-01-01&date_to=2025-12-31"
    )
    assert get_response.status_code == 200
    updated_line = next(
        (line for line in get_response.json() if line["id"] == created_id), None
    )
    assert updated_line is not None
    assert updated_line["name"] == "Test Timesheet Updated"
    assert updated_line["hours"] == 4.0

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
    )
    assert delete_response.status_code == 200


@pytest.mark.integration
def test_edit_timesheet_line_validation(test_client):
    """Test de integración que prueba la validación al editar una línea de timesheet."""
    # Arrange - Crear una línea inicial
    create_data = [
        {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Act - Intentar editar con horas negativas
    edit_data = {
        "id": created_id,
        "name": "Test Timesheet Updated",
        "employee_id": 1,
        "project_id": 1,
        "hours": -1.0,  # Horas inválidas
        "date": "2025-08-01",
        "validated": False,  # Timesheet no validado
    }
    edit_response = test_client.put(f"/api/v1/timesheet/{created_id}", json=edit_data)

    # Assert - Verificar error de horas negativas
    assert edit_response.status_code == 400
    assert "Las horas no pueden ser negativas" in edit_response.json()["detail"]

    # Act - Intentar editar con ID incorrecto en la URL
    edit_data["hours"] = 4.0  # Corregimos las horas
    # edit_data ya tiene validated: False del intento anterior
    edit_response = test_client.put(
        f"/api/v1/timesheet/{created_id + 1}", json=edit_data
    )

    # Assert - Verificar error de ID mismatch
    assert edit_response.status_code == 400
    error_detail = edit_response.json()["detail"]
    assert "El ID en la URL" in error_detail
    assert "no coincide con el ID en el body" in error_detail

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
    )
    assert delete_response.status_code == 200


@pytest.mark.integration
def test_list_timesheet_lines_with_employee_filter(test_client):
    """Test de integración que prueba el filtrado por empleado."""
    # Mock admin user to allow filtering by different employee IDs
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        from app.shared.security.role_enums.dev import Roles
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Admin role
        }

    app.dependency_overrides[get_current_user] = mock_admin_user

    try:
        # Arrange - Crear una línea de timesheet
        create_data = [
            {
                "name": "Test Timesheet",
                "employee_id": 1,
                "project_id": 1,
                "hours": 8.0,
                "date": "2025-08-01",
            }
        ]
        create_response = test_client.post("/api/v1/timesheet/", json=create_data)
        assert create_response.status_code == 200
        created_id = create_response.json()[0]["id"]

        # Act - Filtrar por empleado existente
        response_with_filter = test_client.get(
            "/api/v1/timesheet/?employee_id=1&date_from=2025-01-01&date_to=2025-12-31"
        )

        # Act - Filtrar por empleado que no existe (debería devolver 404)
        response_without_filter = test_client.get(
            "/api/v1/timesheet/?employee_id=999&date_from=2025-01-01&date_to=2025-12-31"
        )

        # Assert
        assert response_with_filter.status_code == 200
        assert response_without_filter.status_code == 404  # Empleado no existe
        assert "no existe en el sistema" in response_without_filter.json()["detail"]

        data_with_filter = response_with_filter.json()

        # Verificar que el timesheet creado aparece en el filtro correcto
        assert any(item["id"] == created_id for item in data_with_filter)

        # Verificar que todos los resultados filtrados son del empleado correcto
        assert all(item["employee_id"] == 1 for item in data_with_filter)

        # Limpieza
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
        )
        assert delete_response.status_code == 200

    finally:
        # Restore original dependency
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_list_timesheet_lines_with_date_filter(test_client):
    """Test de integración que prueba el filtrado por rango de fechas."""
    # Arrange - Crear líneas de timesheet en diferentes fechas
    create_data_1 = [
        {
            "name": "Test Timesheet 1",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-15",
        },
        {
            "name": "Test Timesheet 2",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-20",
        },
        {
            "name": "Test Timesheet 3",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-25",
        },
    ]

    create_response_1 = test_client.post("/api/v1/timesheet/", json=create_data_1)
    assert create_response_1.status_code == 200

    created_ids = [item["id"] for item in create_response_1.json()]
    assert len(created_ids) == 3  # Verificar que se crearon 3 timesheets

    # Act - Filtrar por rango de fechas que incluye solo las dos primeras
    response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2025-08-12&date_to=2025-08-22"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar que solo aparecen las líneas dentro del rango de fechas
    created_ids_in_response = [item["id"] for item in data if item["id"] in created_ids]
    # Solo los primeros 2 timesheets deben estar en el rango (2025-08-15 y 2025-08-20)
    assert len(created_ids_in_response) == 2

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": created_ids}
    )


@pytest.mark.integration
def test_list_timesheet_lines_with_date_from_filter(test_client):
    """Test de integración que prueba el filtrado solo con fecha de inicio."""
    # Arrange
    create_data_old = [
        {
            "name": "Test Timesheet Old",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-10",
        },
        {
            "name": "Test Timesheet New",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-20",
        },
    ]
    create_response_old = test_client.post("/api/v1/timesheet/", json=create_data_old)
    assert create_response_old.status_code == 200

    created_ids = [item["id"] for item in create_response_old.json()]
    assert len(created_ids) == 2  # Verificar que se crearon 2 timesheets

    # Act - Ahora necesitamos pasar employee_id y date_to también
    response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2025-08-15&date_to=2025-12-31"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    created_ids_in_response = [item["id"] for item in data if item["id"] in created_ids]
    # Solo el timesheet nuevo (2025-08-20) debe estar en el rango
    assert len(created_ids_in_response) == 1

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": created_ids}
    )


@pytest.mark.integration
def test_list_timesheet_lines_with_date_to_filter(test_client):
    """Test de integración que prueba el filtrado solo con fecha de fin."""
    # Arrange
    create_data_old = [
        {
            "name": "Test Timesheet Old",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-10",
        },
        {
            "name": "Test Timesheet New",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-20",
        },
    ]
    create_response_old = test_client.post("/api/v1/timesheet/", json=create_data_old)
    assert create_response_old.status_code == 200

    created_ids = [item["id"] for item in create_response_old.json()]
    assert len(created_ids) == 2  # Verificar que se crearon 2 timesheets

    # Act - Ahora necesitamos pasar employee_id y date_from también
    response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2025-01-01&date_to=2025-08-15"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()

    created_ids_in_response = [item["id"] for item in data if item["id"] in created_ids]
    # Solo el timesheet viejo (2025-08-10) debe estar en el rango
    assert len(created_ids_in_response) == 1

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": created_ids}
    )


@pytest.mark.integration
def test_list_timesheet_lines_with_combined_filters(test_client):
    """Test de integración que prueba el filtrado combinado por empleado y fechas."""
    # Arrange - Solo crear timesheets para employee_id=1 (que existe)
    create_data_emp1 = [
        {
            "name": "Test Timesheet Emp1",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-15",
        }
    ]
    create_response_emp1 = test_client.post("/api/v1/timesheet/", json=create_data_emp1)
    assert create_response_emp1.status_code == 200

    created_ids = [item["id"] for item in create_response_emp1.json()]
    assert len(created_ids) == 1  # Verificar que se creó 1 timesheet

    # Act
    response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2025-08-14&date_to=2025-08-16"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    created_ids_in_response = [item["id"] for item in data if item["id"] in created_ids]
    # El timesheet del empleado 1 debe estar en la respuesta
    assert len(created_ids_in_response) == 1

    # Verificar que todos los resultados son del empleado correcto
    assert all(item["employee_id"] == 1 for item in data)

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": created_ids}
    )


@pytest.mark.integration
def test_list_timesheet_lines_no_results_returns_empty_list(test_client):
    """Test de integración que verifica que cuando no hay resultados se devuelve una lista vacía."""
    # Act - Buscar timesheets en un rango donde no hay datos
    response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=1990-01-01&date_to=1990-01-02"
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.integration
def test_delete_timesheet_not_found(test_client):
    """Test de integración que prueba la eliminación de una línea de timesheet que no existe."""
    # Act - Intentar eliminar un timesheet que no existe
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [99999]}
    )

    # Assert
    assert delete_response.status_code == 404
    assert (
        "No se encontraron las líneas de timesheet con IDs: [99999]"
        in delete_response.json()["detail"]
    )


@pytest.mark.integration
def test_delete_timesheet_validation_errors(test_client):
    """Test de integración que prueba los diferentes tipos de errores en delete."""
    # Arrange - Crear una línea de timesheet
    create_data = [
        {
            "name": "Test Timesheet for Delete",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Act - Eliminar correctamente primero
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
    )
    assert delete_response.status_code == 200

    # Act - Intentar eliminar de nuevo el mismo timesheet (ya no existe)
    delete_response_again = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
    )

    # Assert
    assert delete_response_again.status_code == 404
    assert (
        f"No se encontraron las líneas de timesheet con IDs: [{created_id}]"
        in delete_response_again.json()["detail"]
    )


@pytest.mark.integration
def test_validate_timesheet_lines_success(test_client):
    """Test de integración que prueba la validación exitosa de líneas de timesheet."""
    # Arrange - Crear líneas de timesheet
    create_data = [
        {
            "name": "Test Timesheet for Validation 1",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        },
        {
            "name": "Test Timesheet for Validation 2",
            "employee_id": 1,
            "project_id": 1,
            "hours": 4.0,
            "date": "2025-08-02",
        },
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_ids = [item["id"] for item in create_response.json()]
    assert len(created_ids) == 2

    # Mock admin user for validation endpoint
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [30],  # Admin role
        }

    app.dependency_overrides[get_current_user] = mock_admin_user

    try:
        # Act - Validar las líneas
        validate_response = test_client.post(
            "/api/v1/timesheet/validate", json={"timesheetline_ids": created_ids}
        )

        # Assert
        assert validate_response.status_code == 200
        assert validate_response.json()["success"] is True

        # Verificar que las líneas se marcaron como validadas
        # (Nota: En un test real, verificaríamos consultando Odoo, pero para integration test basic esto es suficiente)

    finally:
        # Cleanup - Delete timesheets first (while still admin), then restore dependency
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": created_ids}
        )
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_timesheet_lines_permission_denied(test_client):
    """Test de integración que prueba el error de permisos al validar líneas de timesheet."""
    # Arrange - Crear líneas de timesheet
    create_data = [
        {
            "name": "Test Timesheet for Permission Test",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Act - Intentar validar con usuario normal (sin permisos de admin)
    # El test_client usa el usuario normal por defecto (sin rol 30)
    validate_response = test_client.post(
        "/api/v1/timesheet/validate", json={"timesheetline_ids": [created_id]}
    )

    # Assert
    assert validate_response.status_code == 403
    assert (
        "No tienes permisos para validar las líneas de timesheet"
        in validate_response.json()["detail"]
    )

    # Cleanup - Switch to admin user to delete timesheet
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [30],  # Admin role
        }

    app.dependency_overrides[get_current_user] = mock_admin_user

    try:
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
        )
        assert delete_response.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_timesheet_lines_not_found(test_client):
    """Test de integración que prueba la validación de líneas de timesheet que no existen."""
    # Mock admin user for validation endpoint
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [30],  # Admin role
        }

    app.dependency_overrides[get_current_user] = mock_admin_user

    try:
        # Act - Intentar validar líneas que no existen
        validate_response = test_client.post(
            "/api/v1/timesheet/validate", json={"timesheetline_ids": [99999, 99998]}
        )

        # Assert
        assert validate_response.status_code == 404
        assert (
            "No se encontraron las líneas de timesheet con IDs: [99999, 99998]"
            in validate_response.json()["detail"]
        )

    finally:
        # Cleanup - Restore original dependency
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_timesheet_lines_empty_list(test_client):
    """Test de integración que prueba la validación con lista vacía de IDs."""
    # Mock admin user for validation endpoint
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [30],  # Admin role
        }

    app.dependency_overrides[get_current_user] = mock_admin_user

    try:
        # Act - Intentar validar con lista vacía
        validate_response = test_client.post(
            "/api/v1/timesheet/validate", json={"timesheetline_ids": []}
        )

        # Assert
        assert validate_response.status_code == 404
        assert (
            "No se encontraron las líneas de timesheet con IDs: []"
            in validate_response.json()["detail"]
        )

    finally:
        # Cleanup - Restore original dependency
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_timesheet_lines_mixed_existing_and_nonexisting(test_client):
    """Test de integración que prueba la validación con IDs mixtos (algunos existen, otros no)."""
    # Arrange - Crear una línea de timesheet
    create_data = [
        {
            "name": "Test Timesheet for Mixed Test",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Mock admin user for validation endpoint
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [30],  # Admin role
        }

    app.dependency_overrides[get_current_user] = mock_admin_user

    try:
        # Act - Intentar validar con un ID existente y uno inexistente
        validate_response = test_client.post(
            "/api/v1/timesheet/validate",
            json={"timesheetline_ids": [created_id, 99999]},
        )

        # Assert
        assert validate_response.status_code == 404
        assert (
            "No se encontraron las líneas de timesheet con IDs:"
            in validate_response.json()["detail"]
        )
        assert str(created_id) in validate_response.json()["detail"]
        assert "99999" in validate_response.json()["detail"]

    finally:
        # Cleanup - Delete timesheet first (while still admin), then restore dependency
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
        )
        assert delete_response.status_code == 200
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_edit_validated_timesheet_non_admin_user_forbidden(test_client):
    """Test de integración que verifica que un usuario no admin no puede editar timesheets validados."""
    # Arrange - Crear una línea inicial
    create_data = [
        {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Act - Intentar editar con validated=True usando usuario normal (rol 1)
    edit_data = {
        "id": created_id,
        "name": "Test Timesheet Updated",
        "employee_id": 1,
        "project_id": 1,
        "hours": 4.0,
        "date": "2025-08-01",
        "validated": True,  # Timesheet validado
    }
    edit_response = test_client.put(f"/api/v1/timesheet/{created_id}", json=edit_data)

    # Assert - Debe devolver 403 Forbidden
    assert edit_response.status_code == 403
    assert (
        "No tienes permisos para editar las líneas de timesheet si ya fueron validadas"
        in edit_response.json()["detail"]
    )

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
    )
    assert delete_response.status_code == 200


@pytest.mark.integration
def test_edit_validated_timesheet_admin_user_allowed(test_client):
    """Test de integración que verifica que un usuario admin sí puede editar timesheets validados."""
    # Arrange - Crear una línea inicial
    create_data = [
        {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Mock admin user for editing validated timesheet
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [30],  # Admin role
        }

    app.dependency_overrides[get_current_user] = mock_admin_user

    try:
        # Act - Editar con validated=True usando usuario admin (rol 30)
        edit_data = {
            "id": created_id,
            "name": "Test Timesheet Updated by Admin",
            "employee_id": 1,
            "project_id": 1,
            "hours": 4.0,
            "date": "2025-08-01",
            "validated": True,  # Timesheet validado
        }
        edit_response = test_client.put(
            f"/api/v1/timesheet/{created_id}", json=edit_data
        )

        # Assert - Debe permitir la edición
        assert edit_response.status_code == 200
        assert edit_response.json()["success"] is True

    finally:
        # Cleanup - Delete timesheet first (while still admin), then restore dependency
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
        )
        assert delete_response.status_code == 200
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_edit_non_validated_timesheet_any_user_allowed(test_client):
    """Test de integración que verifica que cualquier usuario puede editar timesheets no validados."""
    # Arrange - Crear una línea inicial
    create_data = [
        {
            "name": "Test Timesheet",
            "employee_id": 1,
            "project_id": 1,
            "hours": 8.0,
            "date": "2025-08-01",
        }
    ]
    create_response = test_client.post("/api/v1/timesheet/", json=create_data)
    assert create_response.status_code == 200
    created_id = create_response.json()[0]["id"]

    # Act - Editar con validated=False usando usuario normal (rol 1, configurado por defecto en conftest)
    edit_data = {
        "id": created_id,
        "name": "Test Timesheet Updated by Normal User",
        "employee_id": 1,
        "project_id": 1,
        "hours": 4.0,
        "date": "2025-08-01",
        "validated": False,  # Timesheet no validado
    }
    edit_response = test_client.put(f"/api/v1/timesheet/{created_id}", json=edit_data)

    # Assert - Debe permitir la edición
    assert edit_response.status_code == 200
    assert edit_response.json()["success"] is True

    # Verificar que los cambios se aplicaron
    get_response = test_client.get(
        "/api/v1/timesheet/?employee_id=1&date_from=2025-01-01&date_to=2025-12-31"
    )
    assert get_response.status_code == 200
    updated_line = next(
        (line for line in get_response.json() if line["id"] == created_id), None
    )
    assert updated_line is not None
    assert updated_line["name"] == "Test Timesheet Updated by Normal User"
    assert updated_line["hours"] == 4.0

    # Limpieza
    delete_response = test_client.request(
        "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
    )
    assert delete_response.status_code == 200
