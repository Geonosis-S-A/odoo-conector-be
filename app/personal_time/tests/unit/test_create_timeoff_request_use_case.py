import pytest
from datetime import date, timedelta
from unittest.mock import Mock
from app.personal_time.application.use_cases.create_timeoff_request import CreateTimeOffRequestUseCase
from app.personal_time.domain.models import TimeOffRequestResult
from app.personal_time.domain.gateway import TimeOffGateway


class TestCreateTimeOffRequestUseCase:
    """Tests unitarios para el caso de uso CreateTimeOffRequestUseCase."""

    @pytest.fixture
    def mock_gateway(self):
        """Fixture que proporciona un gateway mock."""
        return Mock(spec=TimeOffGateway)

    @pytest.fixture
    def use_case(self, mock_gateway):
        """Fixture que proporciona una instancia del caso de uso."""
        return CreateTimeOffRequestUseCase(mock_gateway)

    @pytest.fixture
    def valid_dates(self):
        """Fixture que proporciona fechas válidas para las pruebas."""
        tomorrow = date.today() + timedelta(days=1)
        day_after_tomorrow = date.today() + timedelta(days=2)
        return tomorrow, day_after_tomorrow

    def test_execute_success(self, use_case, mock_gateway, valid_dates):
        """Test que verifica la ejecución exitosa del caso de uso."""
        # Arrange
        start_date, end_date = valid_dates
        expected_result = TimeOffRequestResult.success_result(123)
        mock_gateway.create_timeoff_request.return_value = expected_result

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date,
            description="Vacaciones de prueba"
        )

        # Assert
        assert result.success is True
        assert result.request_id == 123
        assert "exitosamente" in result.message
        mock_gateway.create_timeoff_request.assert_called_once()

        # Verificar que se llamó con los parámetros correctos
        call_args = mock_gateway.create_timeoff_request.call_args[0][0]
        assert call_args.employee_id == 1
        assert call_args.holiday_status_id == 2
        assert call_args.request_date_from == start_date
        assert call_args.request_date_to == end_date
        assert call_args.name == "Vacaciones de prueba"

    def test_execute_gateway_error(self, use_case, mock_gateway, valid_dates):
        """Test que verifica el manejo de errores del gateway."""
        # Arrange
        start_date, end_date = valid_dates
        gateway_error = TimeOffRequestResult.error_result("Error de Odoo")
        mock_gateway.create_timeoff_request.return_value = gateway_error

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date
        )

        # Assert
        assert result.success is False
        assert result.request_id is None
        assert "Error de Odoo" in result.message

    def test_execute_invalid_employee_id(self, use_case, valid_dates):
        """Test que verifica la validación de employee_id inválido."""
        # Arrange
        start_date, end_date = valid_dates

        # Act
        result = use_case.execute(
            employee_id=0,  # ID inválido
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date
        )

        # Assert
        assert result.success is False
        assert "employee_id debe ser un entero positivo" in result.message

    def test_execute_invalid_holiday_status_id(self, use_case, valid_dates):
        """Test que verifica la validación de holiday_status_id inválido."""
        # Arrange
        start_date, end_date = valid_dates

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=-1,  # ID inválido
            request_date_from=start_date,
            request_date_to=end_date
        )

        # Assert
        assert result.success is False
        assert "holiday_status_id debe ser un entero positivo" in result.message

    def test_execute_date_from_after_date_to(self, use_case):
        """Test que verifica la validación cuando fecha inicio > fecha fin."""
        # Arrange
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=tomorrow,  # Después
            request_date_to=today        # Antes
        )

        # Assert
        assert result.success is False
        assert "fecha de inicio no puede ser posterior" in result.message

    def test_execute_past_dates(self, use_case):
        """Test que verifica la validación de fechas pasadas."""
        # Arrange
        yesterday = date.today() - timedelta(days=1)
        day_before_yesterday = date.today() - timedelta(days=2)

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=day_before_yesterday,
            request_date_to=yesterday
        )

        # Assert
        assert result.success is False
        assert "fechas pasadas" in result.message

    def test_execute_empty_description(self, use_case, valid_dates):
        """Test que verifica la validación de descripción vacía."""
        # Arrange
        start_date, end_date = valid_dates

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date,
            description="   "  # Solo espacios
        )

        # Assert
        assert result.success is False
        assert "no puede estar vacía" in result.message

    def test_execute_description_too_long(self, use_case, valid_dates):
        """Test que verifica la validación de descripción muy larga."""
        # Arrange
        start_date, end_date = valid_dates
        long_description = "x" * 501  # Más de 500 caracteres

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date,
            description=long_description
        )

        # Assert
        assert result.success is False
        assert "no puede exceder 500 caracteres" in result.message

    def test_execute_default_description(self, use_case, mock_gateway, valid_dates):
        """Test que verifica el uso de descripción por defecto."""
        # Arrange
        start_date, end_date = valid_dates
        expected_result = TimeOffRequestResult.success_result(456)
        mock_gateway.create_timeoff_request.return_value = expected_result

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date
            # No se proporciona descripción
        )

        # Assert
        assert result.success is True
        call_args = mock_gateway.create_timeoff_request.call_args[0][0]
        assert call_args.name == "Solicitud de tiempo personal"

    def test_execute_with_validation_success(self, use_case, mock_gateway, valid_dates):
        """Test que verifica la ejecución exitosa con validaciones extendidas."""
        # Arrange
        start_date, end_date = valid_dates
        expected_result = TimeOffRequestResult.success_result(789)
        mock_gateway.create_timeoff_request.return_value = expected_result

        # Act
        result = use_case.execute_with_validation(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date,
            description="Vacaciones con validación extendida"
        )

        # Assert
        assert result.success is True
        assert result.request_id == 789

    def test_execute_with_validation_long_duration(self, use_case, mock_gateway):
        """Test que verifica la validación de duración muy larga."""
        # Arrange
        start_date = date.today() + timedelta(days=1)
        end_date = start_date + timedelta(days=400)  # Más de 365 días

        # Act
        result = use_case.execute_with_validation(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date
        )

        # Assert
        assert result.success is False
        assert "no puede exceder" in result.message

    def test_use_case_initialization(self, mock_gateway):
        """Test que verifica la correcta inicialización del caso de uso."""
        # Act
        use_case = CreateTimeOffRequestUseCase(mock_gateway)

        # Assert
        assert use_case.timeoff_gateway is mock_gateway

    def test_gateway_exception_handling(self, use_case, mock_gateway, valid_dates):
        """Test que verifica el manejo de excepciones del gateway."""
        # Arrange
        start_date, end_date = valid_dates
        mock_gateway.create_timeoff_request.side_effect = Exception("Error de conexión")

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=start_date,
            request_date_to=end_date
        )

        # Assert
        assert result.success is False
        assert "Error en el caso de uso CreateTimeOffRequest" in result.message
        assert "Error de conexión" in result.message

    def test_invalid_date_types(self, use_case):
        """Test que verifica la validación de tipos de fecha inválidos."""
        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from="2024-01-01",  # String en lugar de date
            request_date_to=date.today() + timedelta(days=1)
        )

        # Assert
        assert result.success is False
        assert "debe ser una fecha válida" in result.message

    def test_same_day_request(self, use_case, mock_gateway):
        """Test que verifica solicitudes para el mismo día."""
        # Arrange
        tomorrow = date.today() + timedelta(days=1)
        expected_result = TimeOffRequestResult.success_result(999)
        mock_gateway.create_timeoff_request.return_value = expected_result

        # Act
        result = use_case.execute(
            employee_id=1,
            holiday_status_id=2,
            request_date_from=tomorrow,
            request_date_to=tomorrow  # Mismo día
        )

        # Assert
        assert result.success is True
        assert result.request_id == 999
