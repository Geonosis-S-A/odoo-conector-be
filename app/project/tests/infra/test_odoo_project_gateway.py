from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
import pytest
from app.project.domain.models import Project
from app.project.infra.external.odd_project_gateway import OdooProjectGateway


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooProjectGateway:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.odoo_client = get_odoo_connection()
        self.gateway = OdooProjectGateway(self.odoo_client)
        yield

    def test_returns_all_projects_for_user(self):
        # Arrange
        test_user_id = 2  # ID de usuario de prueba

        # Act
        projects = self.gateway.all(test_user_id)

        # Debug information
        print("\nProyectos encontrados:")
        for project in projects:
            print(f"ID: {project.id}, Nombre: {project.name}")

        # Assert
        assert len(projects) > 0
        assert all(isinstance(project, Project) for project in projects)
        assert all(hasattr(project, "id") for project in projects)
        assert all(hasattr(project, "name") for project in projects)
        assert all(isinstance(project.id, int) for project in projects)
        assert all(isinstance(project.name, str) for project in projects)
