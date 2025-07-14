import pytest
from unittest.mock import Mock
from app.project.application.use_cases.obtener_proyectos import ObtenerProyectosUseCase
from app.project.domain.models import Project
from app.project.domain.gateway import ProjectGateway


class TestObtenerProyectosUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=ProjectGateway)

    @pytest.fixture
    def use_case(self, mock_gateway):
        return ObtenerProyectosUseCase(mock_gateway)

    def test_execute_returns_all_projects_successfully(self, use_case, mock_gateway):
        """Test que verifica que el caso de uso retorna todos los proyectos correctamente."""
        # Arrange
        test_projects = [
            Project(id=1, name="Proyecto Alpha"),
            Project(id=2, name="Proyecto Beta"),
            Project(id=3, name="Proyecto Gamma"),
        ]
        mock_gateway.all.return_value = test_projects

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with()
        assert len(result) == 3
        assert all(isinstance(project, Project) for project in result)
        assert result[0].id == 1
        assert result[0].name == "Proyecto Alpha"
        assert result[1].id == 2
        assert result[1].name == "Proyecto Beta"
        assert result[2].id == 3
        assert result[2].name == "Proyecto Gamma"

    def test_execute_removes_duplicate_projects(self, use_case, mock_gateway):
        """Test que verifica que el caso de uso elimina proyectos duplicados correctamente."""
        # Arrange - Simulamos proyectos duplicados (mismo ID)
        test_projects = [
            Project(id=1, name="Proyecto Alpha"),
            Project(id=2, name="Proyecto Beta"),
            Project(
                id=1, name="Proyecto Alpha Duplicado"
            ),  # Duplicado con diferente nombre
            Project(id=3, name="Proyecto Gamma"),
            Project(id=2, name="Proyecto Beta Duplicado"),  # Otro duplicado
        ]
        mock_gateway.all.return_value = test_projects

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with()
        assert len(result) == 3  # Solo 3 proyectos únicos

        # Verificar que solo hay un proyecto por ID
        project_ids = [project.id for project in result]
        assert len(set(project_ids)) == len(project_ids)  # No hay IDs duplicados

        # Verificar que se mantiene el primer proyecto encontrado para cada ID
        projects_by_id = {project.id: project for project in result}
        assert projects_by_id[1].name == "Proyecto Alpha"  # Primer nombre encontrado
        assert projects_by_id[2].name == "Proyecto Beta"  # Primer nombre encontrado
        assert projects_by_id[3].name == "Proyecto Gamma"

    def test_execute_returns_empty_list_when_no_projects(self, use_case, mock_gateway):
        """Test que verifica que el caso de uso retorna lista vacía cuando no hay proyectos."""
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with()
        assert result == []
        assert len(result) == 0
        assert isinstance(result, list)

    def test_execute_returns_empty_list_when_gateway_returns_none(
        self, use_case, mock_gateway
    ):
        """Test que verifica que el caso de uso maneja correctamente cuando el gateway retorna None."""
        # Arrange
        mock_gateway.all.return_value = None

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with()
        assert result == []
        assert len(result) == 0
        assert isinstance(result, list)

    def test_execute_handles_single_project(self, use_case, mock_gateway):
        """Test que verifica que el caso de uso maneja correctamente un solo proyecto."""
        # Arrange
        test_projects = [
            Project(id=1, name="Proyecto Único"),
        ]
        mock_gateway.all.return_value = test_projects

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with()
        assert len(result) == 1
        assert isinstance(result[0], Project)
        assert result[0].id == 1
        assert result[0].name == "Proyecto Único"

    def test_execute_preserves_project_properties(self, use_case, mock_gateway):
        """Test que verifica que el caso de uso preserva todas las propiedades de los proyectos."""
        # Arrange
        test_projects = [
            Project(id=42, name="Proyecto con ID especial"),
            Project(
                id=100,
                name="Proyecto con nombre largo y caracteres especiales: áéíóú ñ",
            ),
        ]
        mock_gateway.all.return_value = test_projects

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with()
        assert len(result) == 2

        # Verificar que se preservan los IDs exactos
        assert result[0].id == 42
        assert result[1].id == 100

        # Verificar que se preservan los nombres exactos
        assert result[0].name == "Proyecto con ID especial"
        assert (
            result[1].name
            == "Proyecto con nombre largo y caracteres especiales: áéíóú ñ"
        )

    def test_execute_calls_gateway_without_parameters(self, use_case, mock_gateway):
        """Test que verifica que el caso de uso llama al gateway sin parámetros."""
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        use_case.execute()

        # Assert
        # Verificar que se llama al método all() sin argumentos
        mock_gateway.all.assert_called_once_with()

        # Verificar que no se llama ningún otro método del gateway
        assert len(mock_gateway.method_calls) == 1
        assert mock_gateway.method_calls[0][0] == "all"
        assert mock_gateway.method_calls[0][1] == ()  # Sin argumentos posicionales
        assert mock_gateway.method_calls[0][2] == {}  # Sin argumentos nombrados
