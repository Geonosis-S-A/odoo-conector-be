import pytest
from unittest.mock import Mock

from app.project.application.use_cases.obtener_proyectos_asignados import (
    ObtenerProyectosAsignadosUseCase,
)
from app.project.domain.gateway import ProjectAssignmentGateway
from app.project.domain.models import Project


class TestObtenerProyectosAsignadosUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=ProjectAssignmentGateway)

    @pytest.fixture
    def use_case(self, mock_gateway):
        return ObtenerProyectosAsignadosUseCase(mock_gateway)

    def test_returns_assigned_projects_when_no_user_id(self, use_case, mock_gateway):
        mock_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="P1")
        ]

        result = use_case.execute(employee_id=7, user_id=None)

        assert result == [Project(id=1, name="P1")]
        mock_gateway.get_managed_projects.assert_not_called()

    def test_combines_assigned_and_managed_projects(self, use_case, mock_gateway):
        mock_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="P1")
        ]
        mock_gateway.get_managed_projects.return_value = [
            Project(id=2, name="P2", manager_user_id=100)
        ]

        result = use_case.execute(employee_id=7, user_id=100)

        assert {p.id for p in result} == {1, 2}
        mock_gateway.get_managed_projects.assert_called_once_with(100)

    def test_deduplicates_projects_present_in_both_sets(self, use_case, mock_gateway):
        mock_gateway.get_employee_assigned_projects.return_value = [
            Project(id=1, name="P1")
        ]
        mock_gateway.get_managed_projects.return_value = [
            Project(id=1, name="P1", manager_user_id=100)
        ]

        result = use_case.execute(employee_id=7, user_id=100)

        assert len(result) == 1

    def test_empty_when_nothing_assigned_or_managed(self, use_case, mock_gateway):
        mock_gateway.get_employee_assigned_projects.return_value = []
        mock_gateway.get_managed_projects.return_value = []

        result = use_case.execute(employee_id=7, user_id=100)

        assert result == []
