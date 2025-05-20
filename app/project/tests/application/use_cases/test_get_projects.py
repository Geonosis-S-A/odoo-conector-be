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

    def test_execute_returns_user_projects(self, use_case, mock_gateway):
        # Arrange
        test_projects = [
            Project(id=1, name="Proyecto 1"),
            Project(id=2, name="Proyecto 2"),
        ]
        mock_gateway.all.return_value = test_projects
        test_user_id = 1

        # Act
        result = use_case.execute(test_user_id)
        # Debug information
        print("\nProyectos encontrados:")
        for project in result:
            print(f"ID: {project.id}, Nombre: {project.name}")

        # Assert
        mock_gateway.all.assert_called_once_with(test_user_id)
        assert len(result) == 2
        assert all(isinstance(project, Project) for project in result)
        assert result[0].id == 1
        assert result[0].name == "Proyecto 1"
        assert result[1].id == 2
        assert result[1].name == "Proyecto 2"
