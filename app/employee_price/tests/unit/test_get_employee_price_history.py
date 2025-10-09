import pytest
from unittest.mock import Mock
from datetime import date

from app.employee_price.application.use_cases.get_employee_price_history import (
    GetEmployeePriceHistoryUseCase,
)
from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository


class TestGetEmployeePriceHistoryUseCase:
    @pytest.fixture
    def mock_repository(self):
        """Fixture que proporciona un repositorio mockeado."""
        return Mock(spec=EmployeePriceRepository)

    @pytest.fixture
    def use_case(self, mock_repository):
        """Fixture que proporciona el caso de uso con el repositorio mockeado."""
        return GetEmployeePriceHistoryUseCase(mock_repository)

    @pytest.fixture
    def sample_price_history(self):
        """Fixture que proporciona un historial de precios de prueba."""
        return [
            EmployeePrice(
                id=3,
                user_id=100,
                date_from=date(2024, 1, 1),
                date_to=None,  # Registro actual/abierto
                cost_per_hour=60.0,
            ),
            EmployeePrice(
                id=2,
                user_id=100,
                date_from=date(2023, 6, 1),
                date_to=date(2024, 1, 1),
                cost_per_hour=50.0,
            ),
            EmployeePrice(
                id=1,
                user_id=100,
                date_from=date(2023, 1, 1),
                date_to=date(2023, 6, 1),
                cost_per_hour=40.0,
            ),
        ]

    def test_execute_returns_price_history_successfully(
        self, use_case, mock_repository, sample_price_history
    ):
        """Test que verifica la obtención exitosa del historial de precios."""
        # Arrange
        employee_id = 100
        mock_repository.get_by_user_id.return_value = sample_price_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert result == sample_price_history
        assert len(result) == 3
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_returns_empty_list_when_no_history(
        self, use_case, mock_repository
    ):
        """Test que verifica que se devuelve una lista vacía cuando no hay historial."""
        # Arrange
        employee_id = 999
        mock_repository.get_by_user_id.return_value = []

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert result == []
        assert isinstance(result, list)
        assert len(result) == 0
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_returns_single_price_record(self, use_case, mock_repository):
        """Test que verifica la obtención de un único registro de precio."""
        # Arrange
        employee_id = 100
        single_record = [
            EmployeePrice(
                id=1,
                user_id=employee_id,
                date_from=date(2024, 1, 1),
                date_to=None,
                cost_per_hour=50.0,
            )
        ]
        mock_repository.get_by_user_id.return_value = single_record

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].user_id == employee_id
        assert result[0].cost_per_hour == 50.0
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_returns_multiple_price_records(
        self, use_case, mock_repository, sample_price_history
    ):
        """Test que verifica la obtención de múltiples registros de precio."""
        # Arrange
        employee_id = 100
        mock_repository.get_by_user_id.return_value = sample_price_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 3
        # Verificar que todos los registros pertenecen al empleado correcto
        for price_record in result:
            assert price_record.user_id == employee_id
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_different_employee_ids(self, use_case, mock_repository):
        """Test que verifica la obtención de historiales para diferentes empleados."""
        # Arrange
        employee_id_1 = 100
        employee_id_2 = 200

        history_1 = [
            EmployeePrice(
                id=1,
                user_id=employee_id_1,
                date_from=date(2024, 1, 1),
                date_to=None,
                cost_per_hour=50.0,
            )
        ]

        history_2 = [
            EmployeePrice(
                id=2,
                user_id=employee_id_2,
                date_from=date(2024, 1, 1),
                date_to=None,
                cost_per_hour=70.0,
            )
        ]

        # Act & Assert - Primer empleado
        mock_repository.get_by_user_id.return_value = history_1
        result_1 = use_case.execute(employee_id_1)
        assert len(result_1) == 1
        assert result_1[0].user_id == employee_id_1
        mock_repository.get_by_user_id.assert_called_with(employee_id_1)

        # Act & Assert - Segundo empleado
        mock_repository.get_by_user_id.return_value = history_2
        result_2 = use_case.execute(employee_id_2)
        assert len(result_2) == 1
        assert result_2[0].user_id == employee_id_2
        mock_repository.get_by_user_id.assert_called_with(employee_id_2)

    def test_execute_repository_exception_propagation(
        self, use_case, mock_repository
    ):
        """Test que verifica que las excepciones del repositorio se propagan correctamente."""
        # Arrange
        employee_id = 100
        mock_repository.get_by_user_id.side_effect = Exception(
            "Database connection failed"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(employee_id)

        assert "Database connection failed" in str(exc_info.value)
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_history_including_open_record(
        self, use_case, mock_repository
    ):
        """Test que verifica el historial que incluye un registro abierto (date_to=None)."""
        # Arrange
        employee_id = 100
        history_with_open = [
            EmployeePrice(
                id=2,
                user_id=employee_id,
                date_from=date(2024, 1, 1),
                date_to=None,  # Registro abierto
                cost_per_hour=60.0,
            ),
            EmployeePrice(
                id=1,
                user_id=employee_id,
                date_from=date(2023, 1, 1),
                date_to=date(2024, 1, 1),
                cost_per_hour=50.0,
            ),
        ]
        mock_repository.get_by_user_id.return_value = history_with_open

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 2
        # Verificar que el primer registro está abierto
        assert result[0].date_to is None
        # Verificar que el segundo registro está cerrado
        assert result[1].date_to is not None
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_history_all_closed_records(
        self, use_case, mock_repository
    ):
        """Test que verifica el historial con todos los registros cerrados."""
        # Arrange
        employee_id = 100
        all_closed_history = [
            EmployeePrice(
                id=3,
                user_id=employee_id,
                date_from=date(2024, 1, 1),
                date_to=date(2024, 6, 1),
                cost_per_hour=60.0,
            ),
            EmployeePrice(
                id=2,
                user_id=employee_id,
                date_from=date(2023, 6, 1),
                date_to=date(2024, 1, 1),
                cost_per_hour=50.0,
            ),
            EmployeePrice(
                id=1,
                user_id=employee_id,
                date_from=date(2023, 1, 1),
                date_to=date(2023, 6, 1),
                cost_per_hour=40.0,
            ),
        ]
        mock_repository.get_by_user_id.return_value = all_closed_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 3
        # Verificar que todos los registros tienen date_to
        for record in result:
            assert record.date_to is not None
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_varying_cost_per_hour_values(
        self, use_case, mock_repository
    ):
        """Test que verifica el historial con diferentes valores de cost_per_hour."""
        # Arrange
        employee_id = 100
        varying_costs_history = [
            EmployeePrice(
                id=4,
                user_id=employee_id,
                date_from=date(2024, 7, 1),
                date_to=None,
                cost_per_hour=None,  # Sin costo
            ),
            EmployeePrice(
                id=3,
                user_id=employee_id,
                date_from=date(2024, 1, 1),
                date_to=date(2024, 7, 1),
                cost_per_hour=75.50,  # Decimal
            ),
            EmployeePrice(
                id=2,
                user_id=employee_id,
                date_from=date(2023, 6, 1),
                date_to=date(2024, 1, 1),
                cost_per_hour=50.0,
            ),
            EmployeePrice(
                id=1,
                user_id=employee_id,
                date_from=date(2023, 1, 1),
                date_to=date(2023, 6, 1),
                cost_per_hour=30.0,
            ),
        ]
        mock_repository.get_by_user_id.return_value = varying_costs_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 4
        assert result[0].cost_per_hour is None
        assert result[1].cost_per_hour == 75.50
        assert result[2].cost_per_hour == 50.0
        assert result[3].cost_per_hour == 30.0
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_returns_list_type(self, use_case, mock_repository):
        """Test que verifica que el resultado es siempre una lista."""
        # Arrange
        employee_id = 100
        mock_repository.get_by_user_id.return_value = []

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert isinstance(result, list)
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_employee_id_zero(self, use_case, mock_repository):
        """Test que verifica el comportamiento con employee_id=0."""
        # Arrange
        employee_id = 0
        mock_repository.get_by_user_id.return_value = []

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert result == []
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_negative_employee_id(self, use_case, mock_repository):
        """Test que verifica el comportamiento con employee_id negativo."""
        # Arrange
        employee_id = -1
        mock_repository.get_by_user_id.return_value = []

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert result == []
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_large_employee_id(self, use_case, mock_repository):
        """Test que verifica el comportamiento con employee_id muy grande."""
        # Arrange
        employee_id = 999999999
        mock_repository.get_by_user_id.return_value = []

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert result == []
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_preserves_repository_order(
        self, use_case, mock_repository, sample_price_history
    ):
        """Test que verifica que se preserva el orden devuelto por el repositorio."""
        # Arrange
        employee_id = 100
        mock_repository.get_by_user_id.return_value = sample_price_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert result == sample_price_history
        # Verificar que el orden se mantiene
        assert result[0].id == 3
        assert result[1].id == 2
        assert result[2].id == 1
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_long_history(self, use_case, mock_repository):
        """Test que verifica el manejo de un historial extenso."""
        # Arrange
        employee_id = 100
        # Crear un historial de 10 registros
        long_history = []
        for i in range(10, 0, -1):
            record = EmployeePrice(
                id=i,
                user_id=employee_id,
                date_from=date(2020 + i, 1, 1),
                date_to=date(2020 + i + 1, 1, 1) if i < 10 else None,
                cost_per_hour=30.0 + (i * 5.0),
            )
            long_history.append(record)

        mock_repository.get_by_user_id.return_value = long_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 10
        assert result == long_history
        # Verificar que todos los registros son del empleado correcto
        for record in result:
            assert record.user_id == employee_id
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_repository_called_exactly_once(
        self, use_case, mock_repository, sample_price_history
    ):
        """Test que verifica que el repositorio se llama exactamente una vez."""
        # Arrange
        employee_id = 100
        mock_repository.get_by_user_id.return_value = sample_price_history

        # Act
        use_case.execute(employee_id)

        # Assert
        # Verificar que se llamó exactamente una vez
        assert mock_repository.get_by_user_id.call_count == 1
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_does_not_modify_repository_result(
        self, use_case, mock_repository, sample_price_history
    ):
        """Test que verifica que el caso de uso no modifica el resultado del repositorio."""
        # Arrange
        employee_id = 100
        original_history = sample_price_history.copy()
        mock_repository.get_by_user_id.return_value = sample_price_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        # Verificar que el resultado es el mismo que retornó el repositorio
        assert result == original_history
        assert len(result) == len(original_history)
        # Verificar que los objetos no fueron modificados
        for i, record in enumerate(result):
            assert record.id == original_history[i].id
            assert record.user_id == original_history[i].user_id
            assert record.date_from == original_history[i].date_from
            assert record.date_to == original_history[i].date_to
            assert record.cost_per_hour == original_history[i].cost_per_hour

    def test_execute_with_records_having_same_dates(self, use_case, mock_repository):
        """Test que verifica el manejo de registros con fechas coincidentes (caso edge)."""
        # Arrange
        employee_id = 100
        same_date = date(2024, 1, 1)
        history_with_same_dates = [
            EmployeePrice(
                id=2,
                user_id=employee_id,
                date_from=same_date,
                date_to=None,
                cost_per_hour=60.0,
            ),
            EmployeePrice(
                id=1,
                user_id=employee_id,
                date_from=same_date,
                date_to=same_date,
                cost_per_hour=50.0,
            ),
        ]
        mock_repository.get_by_user_id.return_value = history_with_same_dates

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 2
        assert result[0].date_from == same_date
        assert result[1].date_from == same_date
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_future_dates(self, use_case, mock_repository):
        """Test que verifica el manejo de registros con fechas futuras."""
        # Arrange
        employee_id = 100
        future_history = [
            EmployeePrice(
                id=1,
                user_id=employee_id,
                date_from=date(2030, 1, 1),
                date_to=None,
                cost_per_hour=100.0,
            )
        ]
        mock_repository.get_by_user_id.return_value = future_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 1
        assert result[0].date_from == date(2030, 1, 1)
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

    def test_execute_with_very_old_dates(self, use_case, mock_repository):
        """Test que verifica el manejo de registros con fechas muy antiguas."""
        # Arrange
        employee_id = 100
        old_history = [
            EmployeePrice(
                id=1,
                user_id=employee_id,
                date_from=date(1990, 1, 1),
                date_to=date(2000, 1, 1),
                cost_per_hour=10.0,
            )
        ]
        mock_repository.get_by_user_id.return_value = old_history

        # Act
        result = use_case.execute(employee_id)

        # Assert
        assert len(result) == 1
        assert result[0].date_from == date(1990, 1, 1)
        mock_repository.get_by_user_id.assert_called_once_with(employee_id)

