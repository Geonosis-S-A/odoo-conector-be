import pytest
from unittest.mock import Mock
from datetime import date, timedelta

from app.employee_price.application.use_cases.create_employee_price import (
    CreateEmployeePriceUseCase,
)
from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository


class TestCreateEmployeePriceUseCase:
    @pytest.fixture
    def mock_repository(self):
        """Fixture que proporciona un repositorio mockeado."""
        return Mock(spec=EmployeePriceRepository)

    @pytest.fixture
    def use_case(self, mock_repository):
        """Fixture que proporciona el caso de uso con el repositorio mockeado."""
        return CreateEmployeePriceUseCase(mock_repository)

    @pytest.fixture
    def sample_employee_price(self):
        """Fixture que proporciona un EmployeePrice de prueba."""
        return EmployeePrice(
            id=1,
            user_id=100,
            date_from=date(2024, 1, 1),
            date_to=None,
            cost_per_hour=50.0,
        )

    @pytest.fixture
    def sample_open_record(self):
        """Fixture que proporciona un registro abierto de prueba."""
        return EmployeePrice(
            id=1,
            user_id=100,
            date_from=date(2023, 6, 1),
            date_to=None,  # Registro abierto
            cost_per_hour=45.0,
        )

    def test_execute_creates_employee_price_without_previous_record(
        self, use_case, mock_repository, sample_employee_price
    ):
        """Test que verifica la creación exitosa de un precio sin registro previo."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 50.0

        # No existe registro abierto previo
        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = sample_employee_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result == sample_employee_price
        mock_repository.get_open_record_by_user_id.assert_called_once_with(
            user_id=employee_id
        )
        mock_repository.save.assert_called_once()
        # Verificar que NO se llamó a update (no había registro previo)
        mock_repository.update.assert_not_called()

    def test_execute_creates_employee_price_and_closes_previous_open_record(
        self, use_case, mock_repository, sample_employee_price, sample_open_record
    ):
        """Test que verifica que se cierra el registro previo al crear uno nuevo."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 50.0

        # Existe un registro abierto previo
        mock_repository.get_open_record_by_user_id.return_value = sample_open_record
        mock_repository.save.return_value = sample_employee_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result == sample_employee_price
        mock_repository.get_open_record_by_user_id.assert_called_once_with(
            user_id=employee_id
        )
        
        # Verificar que se actualizó el registro previo cerrándolo
        mock_repository.update.assert_called_once_with(sample_open_record)
        assert sample_open_record.date_to == date_from
        
        # Verificar que se guardó el nuevo registro
        mock_repository.save.assert_called_once()

    def test_execute_with_cost_per_hour_none(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación exitosa con cost_per_hour=None."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = None

        created_price = EmployeePrice(
            id=1,
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=None,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = created_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result == created_price
        assert result.cost_per_hour is None
        mock_repository.save.assert_called_once()

    def test_execute_raises_value_error_for_negative_cost_per_hour(self, use_case):
        """Test que verifica que no se pueden crear precios con cost_per_hour negativo."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = -10.0  # Valor negativo

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(employee_id, date_from, cost_per_hour)

        assert "El costo por hora debe ser mayor a 0" in str(exc_info.value)
        assert "-10.0" in str(exc_info.value)

    def test_execute_raises_value_error_for_zero_cost_per_hour(self, use_case):
        """Test que verifica que no se pueden crear precios con cost_per_hour igual a 0."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 0.0  # Valor cero

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(employee_id, date_from, cost_per_hour)

        assert "El costo por hora debe ser mayor a 0" in str(exc_info.value)
        assert "0.0" in str(exc_info.value)

    def test_execute_with_valid_positive_cost_per_hour(
        self, use_case, mock_repository, sample_employee_price
    ):
        """Test que verifica la creación exitosa con cost_per_hour positivo."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 75.5  # Valor positivo válido

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = sample_employee_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result is not None
        mock_repository.save.assert_called_once()

    def test_execute_closes_previous_record_with_correct_date(
        self, use_case, mock_repository, sample_open_record
    ):
        """Test que verifica que el registro previo se cierra con la fecha correcta."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 3, 15)
        cost_per_hour = 60.0

        # El registro previo estaba abierto desde junio 2023
        mock_repository.get_open_record_by_user_id.return_value = sample_open_record
        mock_repository.save.return_value = EmployeePrice(
            id=2,
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=cost_per_hour,
        )

        # Act
        use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        # El registro previo debe cerrarse con date_to = date_from del nuevo registro
        assert sample_open_record.date_to == date_from
        mock_repository.update.assert_called_once_with(sample_open_record)

    def test_execute_with_different_employee_ids(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación para diferentes employee_ids."""
        # Arrange
        employee_id = 999
        date_from = date(2024, 1, 1)
        cost_per_hour = 100.0

        created_price = EmployeePrice(
            id=5,
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=cost_per_hour,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = created_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        mock_repository.get_open_record_by_user_id.assert_called_once_with(
            user_id=employee_id
        )
        assert result.user_id == employee_id

    def test_execute_with_future_date_from(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación con fecha futura."""
        # Arrange
        employee_id = 100
        date_from = date(2025, 6, 1)  # Fecha futura
        cost_per_hour = 80.0

        created_price = EmployeePrice(
            id=3,
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=cost_per_hour,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = created_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result.date_from == date_from
        mock_repository.save.assert_called_once()

    def test_execute_with_past_date_from(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación con fecha pasada."""
        # Arrange
        employee_id = 100
        date_from = date(2020, 1, 1)  # Fecha pasada
        cost_per_hour = 30.0

        created_price = EmployeePrice(
            id=4,
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=cost_per_hour,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = created_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result.date_from == date_from
        mock_repository.save.assert_called_once()

    def test_execute_repository_save_exception_propagation(
        self, use_case, mock_repository
    ):
        """Test que verifica que las excepciones del repositorio se propagan correctamente."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 50.0

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(employee_id, date_from, cost_per_hour)

        assert "Database connection failed" in str(exc_info.value)
        mock_repository.save.assert_called_once()

    def test_execute_repository_update_exception_propagation(
        self, use_case, mock_repository, sample_open_record
    ):
        """Test que verifica que las excepciones en update se propagan correctamente."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 50.0

        mock_repository.get_open_record_by_user_id.return_value = sample_open_record
        mock_repository.update.side_effect = Exception("Update failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(employee_id, date_from, cost_per_hour)

        assert "Update failed" in str(exc_info.value)
        mock_repository.update.assert_called_once()
        # No debe llegar a llamar save si update falla
        mock_repository.save.assert_not_called()

    def test_execute_with_very_high_cost_per_hour(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación con un costo por hora muy alto."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 1000.0  # Valor muy alto pero válido

        created_price = EmployeePrice(
            id=1,
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=cost_per_hour,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = created_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result is not None
        mock_repository.save.assert_called_once()

    def test_execute_with_fractional_cost_per_hour(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación con costo por hora decimal."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 45.75  # Valor decimal

        created_price = EmployeePrice(
            id=1,
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=cost_per_hour,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = created_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result is not None
        mock_repository.save.assert_called_once()

    def test_execute_multiple_sequential_records(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación de múltiples registros secuenciales."""
        # Arrange
        employee_id = 100
        
        # Primer registro
        first_date = date(2024, 1, 1)
        first_cost = 40.0
        first_record = EmployeePrice(
            id=1,
            user_id=employee_id,
            date_from=first_date,
            date_to=None,
            cost_per_hour=first_cost,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = first_record

        # Act - Crear primer registro
        result1 = use_case.execute(employee_id, first_date, first_cost)

        # Assert primer registro
        assert result1 == first_record
        mock_repository.update.assert_not_called()

        # Arrange - Segundo registro
        second_date = date(2024, 6, 1)
        second_cost = 50.0
        second_record = EmployeePrice(
            id=2,
            user_id=employee_id,
            date_from=second_date,
            date_to=None,
            cost_per_hour=second_cost,
        )

        # Ahora existe el primer registro abierto
        mock_repository.get_open_record_by_user_id.return_value = first_record
        mock_repository.save.return_value = second_record

        # Act - Crear segundo registro
        result2 = use_case.execute(employee_id, second_date, second_cost)

        # Assert segundo registro
        assert result2 == second_record
        # El primer registro debe haberse cerrado con la fecha del segundo
        assert first_record.date_to == second_date
        mock_repository.update.assert_called_with(first_record)

    def test_execute_validates_cost_per_hour_before_checking_repository(
        self, use_case, mock_repository
    ):
        """Test que verifica que la validación de cost_per_hour ocurre antes de consultar el repositorio."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = -50.0  # Inválido

        # Act & Assert
        with pytest.raises(ValueError):
            use_case.execute(employee_id, date_from, cost_per_hour)

        # No debe haber consultado el repositorio debido a la validación temprana
        mock_repository.get_open_record_by_user_id.assert_not_called()
        mock_repository.save.assert_not_called()
        mock_repository.update.assert_not_called()

    def test_execute_returns_created_employee_price_with_id(
        self, use_case, mock_repository
    ):
        """Test que verifica que el registro creado retornado incluye un ID."""
        # Arrange
        employee_id = 100
        date_from = date(2024, 1, 1)
        cost_per_hour = 50.0

        created_price = EmployeePrice(
            id=123,  # ID asignado por la base de datos
            user_id=employee_id,
            date_from=date_from,
            date_to=None,
            cost_per_hour=cost_per_hour,
        )

        mock_repository.get_open_record_by_user_id.return_value = None
        mock_repository.save.return_value = created_price

        # Act
        result = use_case.execute(employee_id, date_from, cost_per_hour)

        # Assert
        assert result.id is not None
        assert result.id == 123
        assert result.user_id == employee_id
        assert result.date_from == date_from
        assert result.date_to is None
        assert result.cost_per_hour == cost_per_hour

