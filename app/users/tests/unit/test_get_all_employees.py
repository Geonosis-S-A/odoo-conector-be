import pytest
from unittest.mock import Mock
from app.users.application.use_cases.get_all_employees import GetAllEmployeesUseCase
from app.users.domain.models import Employee


@pytest.fixture
def employee_gateway_mock():
    return Mock()


@pytest.fixture
def use_case(employee_gateway_mock):
    return GetAllEmployeesUseCase(employee_gateway=employee_gateway_mock)


class TestGetAllEmployeesUseCase:
    def test_execute_returns_all_employees(self, use_case, employee_gateway_mock):
        """Test que verifica que el use case retorna todos los empleados del gateway."""
        # Arrange
        expected_employees = [
            Employee(id=1, email="employee1@test.com", full_name="Employee One"),
            Employee(id=2, email="employee2@test.com", full_name="Employee Two"),
            Employee(id=3, email="employee3@test.com", full_name="Employee Three"),
        ]
        employee_gateway_mock.all.return_value = expected_employees

        # Act
        result = use_case.execute()

        # Assert
        assert result == expected_employees
        employee_gateway_mock.all.assert_called_once()

    def test_execute_returns_empty_list_when_no_employees(
        self, use_case, employee_gateway_mock
    ):
        """Test que verifica que el use case retorna lista vacía cuando no hay empleados."""
        # Arrange
        employee_gateway_mock.all.return_value = []

        # Act
        result = use_case.execute()

        # Assert
        assert result == []
        employee_gateway_mock.all.assert_called_once()

    def test_execute_handles_gateway_exception(self, use_case, employee_gateway_mock):
        """Test que verifica que el use case propaga excepciones del gateway."""
        # Arrange
        employee_gateway_mock.all.side_effect = RuntimeError("Gateway error")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Gateway error"):
            use_case.execute()
