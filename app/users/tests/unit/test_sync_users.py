import pytest
from unittest.mock import Mock
from app.users.application.use_cases.sync_users import SyncUsersUseCase
from app.users.domain.models import User, Employee
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


@pytest.fixture
def odoo_employee_gateway_mock():
    # Crear un mock que simule ser una instancia de OdooEmployeeGateway
    mock_gateway = Mock(spec=OdooEmployeeGateway)
    # Configurar los métodos que se usarán en el test
    mock_gateway.get_all_users_with_roles.return_value = []
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
        odoo_users = [
            {
                "id": 1,
                "email": "employee1@example.com",
                "name": "Employee One",
                "roles": [10, 11],
            },
            {
                "id": 2,
                "email": "employee2@example.com",
                "name": "Employee Two",
                "roles": [12],
            },
        ]
        odoo_employee_gateway_mock.get_all_users_with_roles.return_value = odoo_users
        user_repository_mock.all.return_value = []
        user_repository_mock.update_user.return_value = True

        # Act
        result = use_case.execute()

        # Assert
        assert result["created"] == 2
        assert result["updated"] == 0
        user_repository_mock.save_all.assert_called_once()
        user_repository_mock.update_user.assert_not_called()

    def test_sync_updates_existing_users(
        self, use_case, odoo_employee_gateway_mock, user_repository_mock
    ):
        # Arrange
        odoo_users = [
            {
                "id": 1,
                "email": "employee1@example.com",
                "name": "Employee One Updated",
                "roles": [10, 11, 15],
            },
        ]
        existing_users = [
            User(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
                is_active=True,
                is_superuser=True,
                roles=[10, 11],
            ),
        ]
        odoo_employee_gateway_mock.get_all_users_with_roles.return_value = odoo_users
        user_repository_mock.all.return_value = existing_users
        user_repository_mock.update_user.return_value = True

        # Act
        result = use_case.execute()

        # Assert
        assert result["created"] == 0
        assert result["updated"] == 1
        user_repository_mock.save_all.assert_not_called()
        user_repository_mock.update_user.assert_called_once()

    def test_sync_no_changes(
        self, use_case, odoo_employee_gateway_mock, user_repository_mock
    ):
        # Arrange
        odoo_users = [
            {
                "id": 1,
                "email": "employee1@example.com",
                "name": "Employee One",
                "roles": [10],
            },
        ]
        existing_users = [
            User(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
                is_active=True,
                is_superuser=False,
                roles=[10],
            ),
        ]
        odoo_employee_gateway_mock.get_all_users_with_roles.return_value = odoo_users
        user_repository_mock.all.return_value = existing_users

        # Act
        result = use_case.execute()

        # Assert
        assert result["created"] == 0
        assert result["updated"] == 0
        user_repository_mock.save_all.assert_not_called()
        user_repository_mock.update_user.assert_not_called()
