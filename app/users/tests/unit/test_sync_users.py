import pytest
from unittest.mock import Mock
from app.users.application.use_cases.sync_users import SyncUsersUseCase
from app.users.domain.models import User, Employee
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


@pytest.fixture
def odoo_employee_gateway_mock():
    # Crear un mock que simule ser una instancia de OdooEmployeeGateway
    mock_gateway = Mock(spec=OdooEmployeeGateway)
    # Configurar el método correcto que usa el use case
    mock_gateway.get_all_employees_with_user_data.return_value = []
    return mock_gateway


@pytest.fixture
def user_repository_mock():
    return Mock()


@pytest.fixture
def use_case(odoo_employee_gateway_mock, user_repository_mock):
    return SyncUsersUseCase(
        employee_gateway=odoo_employee_gateway_mock,
        user_repository=user_repository_mock,
    )


class TestSyncUsersUseCase:
    def test_sync_new_employees(
        self, use_case, odoo_employee_gateway_mock, user_repository_mock
    ):
        # Arrange
        odoo_employees_data = [
            {
                "id": 1,
                "name": "Employee One",
                "email": "employee1@example.com",
                "user_id": 1,
                "has_user": True,
                "roles": [10, 11],
            },
            {
                "id": 2,
                "name": "Employee Two",
                "email": "employee2@example.com",
                "user_id": 2,
                "has_user": True,
                "roles": [12],
            },
        ]
        odoo_employee_gateway_mock.get_all_employees_with_user_data.return_value = (
            odoo_employees_data
        )

        # Simular que no hay usuarios existentes
        user_repository_mock.get_by_id.return_value = None
        user_repository_mock.get_by_email.return_value = None
        user_repository_mock.update_user.return_value = True

        # Act
        result = use_case.execute()

        # Assert
        # Como no hay usuarios existentes para actualizar, todos serán errores
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total_processed"] == 2
        assert len(result["errors"]) == 2
        user_repository_mock.update_user.assert_not_called()

    def test_sync_updates_existing_users(
        self, use_case, odoo_employee_gateway_mock, user_repository_mock
    ):
        # Arrange
        odoo_employees_data = [
            {
                "id": 1,
                "name": "Employee One Updated",
                "email": "employee1@example.com",
                "user_id": 1,
                "has_user": True,
                "roles": [10, 11, 15],
            },
        ]
        existing_user = User(
            id=1,
            email="employee1@example.com",
            full_name="Employee One",
            is_active=True,
            is_superuser=True,
            roles=[10, 11],
        )

        odoo_employee_gateway_mock.get_all_employees_with_user_data.return_value = (
            odoo_employees_data
        )
        user_repository_mock.get_by_id.return_value = existing_user
        user_repository_mock.update_user.return_value = True

        # Act
        result = use_case.execute()

        # Assert
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["total_processed"] == 1
        assert len(result["errors"]) == 0
        user_repository_mock.update_user.assert_called_once()

    def test_sync_no_changes(
        self, use_case, odoo_employee_gateway_mock, user_repository_mock
    ):
        # Arrange
        odoo_employees_data = [
            {
                "id": 1,
                "name": "Employee One",
                "email": "employee1@example.com",
                "user_id": 1,
                "has_user": True,
                "roles": [10],
            },
        ]
        existing_user = User(
            id=1,
            email="employee1@example.com",
            full_name="Employee One",
            is_active=True,
            is_superuser=False,
            roles=[10],
        )

        odoo_employee_gateway_mock.get_all_employees_with_user_data.return_value = (
            odoo_employees_data
        )
        user_repository_mock.get_by_id.return_value = existing_user
        user_repository_mock.update_user.return_value = True

        # Act
        result = use_case.execute()

        # Assert
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total_processed"] == 1
        assert len(result["errors"]) == 0
        user_repository_mock.update_user.assert_not_called()

    def test_sync_employee_without_user_id(
        self, use_case, odoo_employee_gateway_mock, user_repository_mock
    ):
        # Arrange - Empleado sin user_id asociado
        odoo_employees_data = [
            {
                "id": 3,
                "name": "Employee Without User",
                "email": "employee3@example.com",
                "user_id": None,
                "has_user": False,
                "roles": [],
            },
        ]
        existing_user = User(
            id=3,
            email="employee3@example.com",
            full_name="Employee Without User Old Name",
            is_active=True,
            is_superuser=False,
            roles=[20, 21],  # Roles locales que deben mantenerse
        )

        odoo_employee_gateway_mock.get_all_employees_with_user_data.return_value = (
            odoo_employees_data
        )
        user_repository_mock.get_by_email.return_value = existing_user
        user_repository_mock.update_user.return_value = True

        # Act
        result = use_case.execute()

        # Assert
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["total_processed"] == 1
        assert len(result["errors"]) == 0

        # Verificar que se llamó update_user con los roles locales mantenidos
        user_repository_mock.update_user.assert_called_once()
        called_user = user_repository_mock.update_user.call_args[0][0]
        assert called_user.full_name == "Employee Without User"  # Nombre actualizado
        assert called_user.roles == [20, 21]  # Roles locales mantenidos

    def test_sync_empty_employees_data(
        self, use_case, odoo_employee_gateway_mock, user_repository_mock
    ):
        # Arrange
        odoo_employee_gateway_mock.get_all_employees_with_user_data.return_value = []

        # Act
        result = use_case.execute()

        # Assert
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total_processed"] == 0
        assert len(result["errors"]) == 0
        user_repository_mock.update_user.assert_not_called()
