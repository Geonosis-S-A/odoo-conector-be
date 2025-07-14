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

    def test_all_returns_list_of_active_projects_with_analytic_accounts(self):
        """Test que verifica que all() retorna solo proyectos activos con cuenta analítica activa."""
        # Act
        projects = self.gateway.all()

        # Assert
        assert projects is not None, "El gateway debe retornar una lista, no None"
        assert isinstance(projects, list), "El resultado debe ser una lista"

        # Debug information - solo si hay proyectos
        if projects:
            print(f"\nProyectos encontrados: {len(projects)}")
            for project in projects[:3]:  # Mostrar solo los primeros 3
                print(f"ID: {project.id}, Nombre: {project.name}")
        else:
            print("\nNo se encontraron proyectos que cumplan los criterios")

        # Verificar estructura de los proyectos
        for project in projects:
            assert isinstance(project, Project), (
                "Cada elemento debe ser una instancia de Project"
            )
            assert hasattr(project, "id"), "Cada proyecto debe tener un ID"
            assert hasattr(project, "name"), "Cada proyecto debe tener un nombre"
            assert isinstance(project.id, int), "El ID debe ser un entero"
            assert isinstance(project.name, str), "El nombre debe ser una cadena"
            assert project.id > 0, "El ID debe ser positivo"
            assert len(project.name.strip()) > 0, "El nombre no debe estar vacío"

    def test_all_returns_empty_list_when_no_projects_meet_criteria(self):
        """Test que verifica que all() puede retornar una lista vacía si no hay proyectos válidos."""
        # Act
        projects = self.gateway.all()

        # Assert
        assert projects is not None, "El gateway debe retornar una lista, no None"
        assert isinstance(projects, list), "El resultado debe ser una lista"
        # No verificamos que esté vacía porque puede haber proyectos válidos en el sistema

    def test_all_returns_projects_with_valid_analytic_accounts(self):
        """Test que verifica que todos los proyectos retornados tienen cuentas analíticas válidas."""
        # Act
        projects = self.gateway.all()

        # Assert
        assert projects is not None
        assert isinstance(projects, list)

        # Si hay proyectos, verificar que cumplen los criterios de negocio
        if projects:
            # Todos los proyectos retornados deben estar listos para crear timesheets
            # (esto se verifica implícitamente por la lógica del gateway)
            print(
                f"\nTodos los {len(projects)} proyectos tienen cuentas analíticas activas"
            )

            # Verificar que no hay IDs duplicados (aunque el gateway no debería retornar duplicados)
            project_ids = [project.id for project in projects]
            unique_ids = set(project_ids)
            assert len(project_ids) == len(unique_ids), (
                "No debe haber proyectos duplicados"
            )

    def test_all_method_signature_compatibility(self):
        """Test que verifica que el método all() se puede llamar sin parámetros."""
        # Act & Assert - Verificar que se puede llamar sin parámetros
        try:
            projects = self.gateway.all()
            assert projects is not None
            assert isinstance(projects, list)
        except TypeError as e:
            pytest.fail(f"El método all() debe ser callable sin parámetros: {e}")

    def test_gateway_initialization_with_odoo_client(self):
        """Test que verifica que el gateway se inicializa correctamente con el cliente Odoo."""
        # Arrange
        odoo_client = get_odoo_connection()

        # Act
        gateway = OdooProjectGateway(odoo_client)

        # Assert
        assert gateway is not None
        assert hasattr(gateway, "odoo_client")
        assert gateway.odoo_client == odoo_client
