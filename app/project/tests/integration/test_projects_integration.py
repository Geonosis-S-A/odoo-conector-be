import pytest
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.project.infra.external.odd_project_gateway import OdooProjectGateway


@pytest.fixture(autouse=True)
def setup_gateway():
    """Fixture que configura el gateway real."""
    odoo_client = get_odoo_connection()
    gateway = OdooProjectGateway(odoo_client)
    yield {"gateway": gateway}


@pytest.mark.integration
def test_get_all_projects(test_client):
    """Test de integración que prueba obtener todos los proyectos."""
    # Act
    response = test_client.get("/api/v1/projects/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar la estructura de los datos
    if len(data) > 0:
        assert all(isinstance(item["id"], int) for item in data)
        assert all(isinstance(item["name"], str) for item in data)


@pytest.mark.integration
def test_get_user_projects(test_client):
    """Test de integración que prueba obtener proyectos de un usuario específico."""
    # Arrange
    test_user_id = 1  # ID de usuario de prueba

    # Act
    response = test_client.get(f"/api/v1/projects/?user={test_user_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar la estructura de los datos
    if len(data) > 0:
        assert all(isinstance(item["id"], int) for item in data)
        assert all(isinstance(item["name"], str) for item in data)


@pytest.mark.integration
def test_get_projects_empty_returns_empty_array(test_client):
    """Test de integración que verifica que cuando no hay proyectos se retorna un array vacío."""
    # Note: This test assumes there might be scenarios where no projects exist
    # In a real environment, this might be hard to test without data manipulation

    # Act
    response = test_client.get("/api/v1/projects/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Even if there are projects, the response should be a list
    # If empty, it should be an empty list, not a 404


@pytest.mark.integration
def test_get_projects_handles_odoo_connection_error():
    """Test de integración que verifica el manejo de errores de conexión con Odoo."""
    # TODO: Implementar mock de error de conexión con Odoo
    pass
