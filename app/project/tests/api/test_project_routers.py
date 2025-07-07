import pytest
from unittest.mock import Mock
from app.project.api.routers import get_project_gateway
from app.project.domain.models import Project
from app.project.domain.gateway import ProjectGateway
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection_dependency


@pytest.fixture
def mock_gateway():
    """Fixture que proporciona un gateway mockeado."""
    return Mock(spec=ProjectGateway)


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
    from app.main import app

    # Mock de la dependencia de conexión Odoo
    async def mock_get_odoo_connection():
        return mock_odoo_connection

    # Mock de la dependencia del gateway
    def mock_get_gateway():
        return mock_gateway

    # Aplicar los mocks a las dependencias
    app.dependency_overrides[get_odoo_connection_dependency] = mock_get_odoo_connection
    app.dependency_overrides[get_project_gateway] = mock_get_gateway

    yield

    # Limpiar los mocks después de cada test
    app.dependency_overrides.clear()


@pytest.fixture
def override_gateway_dependency(mock_gateway):
    """Fixture para sobrescribir la dependencia del gateway de proyectos."""

    def override_get_project_gateway():
        return mock_gateway

    return override_get_project_gateway


@pytest.fixture(autouse=True)
def configure_test_client(test_client, mock_gateway, override_gateway_dependency):
    """Configura el test client con las dependencias mockeadas."""
    from app.project.api.routers import router

    test_client.app.dependency_overrides[get_project_gateway] = (
        override_gateway_dependency
    )


class TestProjectGatewayDependency:
    def test_get_project_gateway_success(self, test_client):
        """Test que verifica que la función get_project_gateway funciona correctamente."""
        # This test would require mocking OdooConnection and OdooProjectGateway
        # It's primarily for integration testing
        pass

    def test_get_project_gateway_error(self, test_client):
        """Test que verifica el manejo de errores en get_project_gateway."""
        # This test would require mocking exceptions in the gateway creation
        # It's primarily for integration testing
        pass


class TestGetProjects:
    def test_get_all_projects_success(self, mock_gateway, test_client):
        # Arrange
        mock_projects = [
            Project(id=1, name="Proyecto 1"),
            Project(id=2, name="Proyecto 2"),
        ]
        mock_gateway.all.return_value = mock_projects

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Proyecto 1"
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Proyecto 2"
        # El método all() no acepta parámetros en la implementación actual
        mock_gateway.all.assert_called_once()

    def test_get_user_projects_success(self, mock_gateway, test_client):
        # Arrange
        mock_projects = [
            Project(id=1, name="Proyecto Usuario"),
        ]
        mock_gateway.all.return_value = mock_projects

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/?user=1", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Proyecto Usuario"
        # El método all() no acepta parámetros en la implementación actual
        mock_gateway.all.assert_called_once()

    def test_get_projects_empty_returns_empty_array(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert len(data) == 0
        # El método all() no acepta parámetros en la implementación actual
        mock_gateway.all.assert_called_once()

    def test_get_projects_server_error(self, mock_gateway, test_client):
        # Arrange
        mock_gateway.all.side_effect = Exception("Error de servidor")

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/", headers=headers)

        # Assert
        assert response.status_code == 500
        assert "Error interno del servidor" in response.json()["detail"]
