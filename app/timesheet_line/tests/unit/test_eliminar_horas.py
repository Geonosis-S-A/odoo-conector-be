import pytest
from unittest.mock import Mock
from datetime import date
from app.timesheet_line.application.use_cases.delete_timesheet import (
    DeleteTimesheetUseCase,
)
from app.timesheet_line.application.use_cases.obtener_horas import (
    ListTimesheetLinesUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetDeleteError,
    TimesheetListError,
)


class TestDeleteTimesheetUseCase:
    @pytest.fixture
    def mock_gateway(self):
        """Fixture que proporciona un gateway mockeado."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_gateway):
        """Fixture que proporciona el caso de uso con el gateway mockeado."""
        return DeleteTimesheetUseCase(mock_gateway)

    def test_delete_timesheet_success(self, use_case, mock_gateway):
        """Test que verifica la eliminación exitosa de una línea de timesheet."""
        # Arrange
        timesheet_id = 1

        # Mock de la respuesta del gateway
        mock_gateway.get_by_id.return_value = DetailedTimesheetLine(
            id=1,
            name="Test Timesheet",
            employee_id=1,
            project=Project(id=1, name="Test Project"),
            task=None,
            hours=8.0,
            date=date(2024, 3, 20),
        )
        mock_gateway.delete.return_value = True

        # Act
        result = use_case.execute(timesheet_id)

        # Assert
        assert result is True
        mock_gateway.get_by_id.assert_called_once_with(1)
        mock_gateway.delete.assert_called_once_with(1)

    def test_delete_timesheet_not_found(self, use_case, mock_gateway):
        """Test que verifica el error cuando no se encuentra la línea a eliminar."""
        # Arrange
        timesheet_id = 999  # ID inexistente

        # Mock de la respuesta del gateway - devuelve None
        mock_gateway.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(
            TimesheetNotFoundError,
            match="No se encontró la línea de timesheet con ID: 999",
        ):
            use_case.execute(timesheet_id)

        # Verificar que se llamó a get_by_id pero no a delete
        mock_gateway.get_by_id.assert_called_once_with(999)
        mock_gateway.delete.assert_not_called()

    def test_delete_timesheet_delete_fails(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando falla la eliminación."""
        # Arrange
        timesheet_id = 1

        # Mock de la respuesta del gateway
        mock_gateway.get_by_id.return_value = DetailedTimesheetLine(
            id=1,
            name="Test Timesheet",
            employee_id=1,
            project=Project(id=1, name="Test Project"),
            task=None,
            hours=8.0,
            date=date(2024, 3, 20),
        )
        mock_gateway.delete.return_value = False

        # Act & Assert
        with pytest.raises(
            TimesheetDeleteError,
            match="Error al eliminar la línea de timesheet con ID 1",
        ):
            use_case.execute(timesheet_id)

        mock_gateway.get_by_id.assert_called_once_with(1)
        mock_gateway.delete.assert_called_once_with(1)

    def test_delete_timesheet_delete_exception(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando delete lanza una excepción."""
        # Arrange
        timesheet_id = 1

        # Mock de la respuesta del gateway
        mock_gateway.get_by_id.return_value = DetailedTimesheetLine(
            id=1,
            name="Test Timesheet",
            employee_id=1,
            project=Project(id=1, name="Test Project"),
            task=None,
            hours=8.0,
            date=date(2024, 3, 20),
        )
        mock_gateway.delete.side_effect = ValueError("Error de conexión")

        # Act & Assert
        with pytest.raises(
            TimesheetDeleteError,
            match="Error al eliminar la línea de timesheet con ID 1",
        ):
            use_case.execute(timesheet_id)

        mock_gateway.get_by_id.assert_called_once_with(1)
        mock_gateway.delete.assert_called_once_with(1)

    def test_delete_timesheet_get_by_id_exception(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando get_by_id lanza una excepción."""
        # Arrange
        timesheet_id = 1

        # Mock de la respuesta del gateway
        mock_gateway.get_by_id.side_effect = ValueError("Error de conexión")

        # Act & Assert
        with pytest.raises(ValueError, match="Error de conexión"):
            use_case.execute(timesheet_id)

        mock_gateway.get_by_id.assert_called_once_with(1)
        mock_gateway.delete.assert_not_called()


class TestListTimesheetLinesUseCase:
    @pytest.fixture
    def mock_timesheet_gateway(self):
        """Fixture que proporciona un timesheet gateway mockeado."""
        return Mock()

    @pytest.fixture
    def mock_employee_gateway(self):
        """Fixture que proporciona un employee gateway mockeado."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_timesheet_gateway, mock_employee_gateway):
        """Fixture que proporciona el caso de uso con los gateways mockeados."""
        return ListTimesheetLinesUseCase(mock_timesheet_gateway, mock_employee_gateway)

    def test_list_timesheets_empty_result_returns_empty_list_corrected_behavior(
        self, use_case, mock_timesheet_gateway, mock_employee_gateway
    ):
        """Test que verifica el comportamiento CORRECTO: cuando no hay timesheets en un rango de fechas,
        debería devolver una lista vacía (no un error 422).

        Este test verifica el comportamiento después de corregir el caso de uso.
        """
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Mock: el empleado existe
        mock_employee_gateway.exists_by_id.return_value = True

        # Mock: no hay timesheets en el rango de fechas (lista vacía)
        mock_timesheet_gateway.all.return_value = []

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        assert result == []
        assert isinstance(result, list)
        assert len(result) == 0

        # Verificar que se llamaron los métodos correctos
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_timesheet_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to
        )
