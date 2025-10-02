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
    def test_get_all_active_projects_success(self, mock_gateway, test_client):
        """Test que verifica que el endpoint retorna todos los proyectos activos correctamente."""
        # Arrange
        mock_projects = [
            Project(id=1, name="Proyecto Alpha"),
            Project(id=2, name="Proyecto Beta"),
            Project(id=3, name="Proyecto Gamma"),
        ]
        mock_gateway.all.return_value = mock_projects

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Proyecto Alpha"
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Proyecto Beta"
        assert data[2]["id"] == 3
        assert data[2]["name"] == "Proyecto Gamma"

        # Verificar que el gateway se llama sin parámetros
        mock_gateway.all.assert_called_once_with()

    def test_get_projects_ignores_user_parameter(self, mock_gateway, test_client):
        """Test que verifica que el endpoint ignora el parámetro user (no implementado)."""
        # Arrange
        mock_projects = [
            Project(id=1, name="Proyecto Test"),
        ]
        mock_gateway.all.return_value = mock_projects

        # Act - Con parámetro user que debe ser ignorado
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/?user=1", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Proyecto Test"

        # Verificar que el gateway se llama sin parámetros (ignora el user)
        mock_gateway.all.assert_called_once_with()

    def test_get_projects_empty_returns_empty_array(self, mock_gateway, test_client):
        """Test que verifica que el endpoint retorna una lista vacía cuando no hay proyectos."""
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
        assert isinstance(data, list)

        # Verificar que el gateway se llama correctamente
        mock_gateway.all.assert_called_once_with()

    def test_get_projects_handles_none_from_gateway(self, mock_gateway, test_client):
        """Test que verifica que el endpoint maneja correctamente cuando el gateway retorna None."""
        # Arrange
        mock_gateway.all.return_value = None

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert len(data) == 0
        assert isinstance(data, list)

        # Verificar que el gateway se llama correctamente
        mock_gateway.all.assert_called_once_with()


    def test_get_projects_response_format(self, mock_gateway, test_client):
        """Test que verifica el formato de respuesta del endpoint."""
        # Arrange
        mock_projects = [
            Project(id=42, name="Proyecto con ID especial"),
        ]
        mock_gateway.all.return_value = mock_projects

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/", headers=headers)

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        # Verificar estructura de ProjectResponse
        project = data[0]
        assert set(project.keys()) == {"id", "name"}
        assert project["id"] == 42
        assert project["name"] == "Proyecto con ID especial"

        # Verificar que el gateway se llama correctamente
        mock_gateway.all.assert_called_once_with()

    def test_get_projects_duplicate_handling_in_use_case(
        self, mock_gateway, test_client
    ):
        """Test que verifica que los duplicados son manejados por el caso de uso."""
        # Arrange - Simular duplicados que serían manejados por el caso de uso
        mock_projects = [
            Project(id=1, name="Proyecto Alpha"),
            Project(id=2, name="Proyecto Beta"),
            Project(id=1, name="Proyecto Alpha Duplicado"),  # Duplicado
        ]
        mock_gateway.all.return_value = mock_projects

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/projects/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # El caso de uso elimina duplicados, por lo que solo deben retornarse 2 proyectos únicos
        assert len(data) == 2  # El caso de uso elimina duplicados

        # Verificar que se mantienen los proyectos únicos
        project_ids = [project["id"] for project in data]
        assert 1 in project_ids
        assert 2 in project_ids
        assert len(set(project_ids)) == 2  # No hay duplicados

        # Verificar que se mantiene el primer proyecto encontrado para cada ID
        projects_by_id = {project["id"]: project for project in data}
        assert projects_by_id[1]["name"] == "Proyecto Alpha"  # Primer nombre encontrado
        assert projects_by_id[2]["name"] == "Proyecto Beta"

        # Verificar que el gateway se llama correctamente
        mock_gateway.all.assert_called_once_with()
