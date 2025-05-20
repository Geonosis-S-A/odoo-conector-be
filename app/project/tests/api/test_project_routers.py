import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.project.api.routers import router, get_project_gateway
from app.project.domain.models import Project
from app.project.domain.gateway import ProjectGateway
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection_dependency
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


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


class TestGetProjects:
    def test_get_all_projects_success(self, mock_gateway):
        # Arrange
        mock_projects = [
            Project(id=1, name="Proyecto 1"),
            Project(id=2, name="Proyecto 2"),
        ]
        mock_gateway.all.return_value = mock_projects

        # Act
        response = client.get("/projects/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Proyecto 1"
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Proyecto 2"
        mock_gateway.all.assert_called_once_with(None)

    def test_get_user_projects_success(self, mock_gateway):
        # Arrange
        mock_projects = [
            Project(id=1, name="Proyecto Usuario"),
        ]
        mock_gateway.all.return_value = mock_projects

        # Act
        response = client.get("/projects/?user=1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Proyecto Usuario"
        mock_gateway.all.assert_called_once_with(1)

    def test_get_projects_empty(self, mock_gateway):
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        response = client.get("/projects/")

        # Assert
        assert response.status_code == 200
        assert response.json() == []
        mock_gateway.all.assert_called_once_with(None)

    def test_get_projects_server_error(self, mock_gateway):
        # Arrange
        mock_gateway.all.side_effect = Exception("Error de servidor")

        # Act
        response = client.get("/projects/")

        # Assert
        assert response.status_code == 500
        assert "Error interno del servidor" in response.json()["detail"]
