import pytest
from unittest.mock import Mock
from app.users.domain.models import Employee, User
from app.users.application.use_cases.sync_users import SyncUsersUseCase


class TestSyncUsersUseCase:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.employee_gateway = Mock()
        self.user_repository = Mock()
        self.use_case = SyncUsersUseCase(
            employee_gateway=self.employee_gateway,
            user_repository=self.user_repository,
        )

    def test_sync_new_employees(self):
        # Arrange
        odoo_employees = [
            Employee(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
            ),
            Employee(
                id=2,
                email="employee2@example.com",
                full_name="Employee Two",
            ),
        ]
        self.employee_gateway.all.return_value = odoo_employees
        self.user_repository.all.return_value = []

        # Act
        self.use_case.execute()

        # Assert
        self.user_repository.save_all.assert_called_once()
        saved_users = self.user_repository.save_all.call_args[0][0]
        assert len(saved_users) == 2
        assert all(isinstance(user, User) for user in saved_users)
        assert all(not user.is_active for user in saved_users)
        assert all(not user.is_superuser for user in saved_users)
        assert all(user.id is None for user in saved_users)

    def test_sync_existing_employees(self):
        # Arrange
        odoo_employees = [
            Employee(
                id=1,
                email="employee1@example.com",
                full_name="Employee One Updated",
            ),
        ]
        existing_users = [
            User(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
                is_active=True,
                is_superuser=False,
            ),
        ]
        self.employee_gateway.all.return_value = odoo_employees
        self.user_repository.all.return_value = existing_users

        # Act
        self.use_case.execute()

        # Assert
        self.user_repository.save_all.assert_called_once()
        saved_users = self.user_repository.save_all.call_args[0][0]
        assert len(saved_users) == 1
        assert saved_users[0].id == 1
        assert saved_users[0].email == "employee1@example.com"
        assert saved_users[0].full_name == "Employee One Updated"
        assert saved_users[0].is_active is True
        assert saved_users[0].is_superuser is False

    def test_sync_mixed_employees(self):
        # Arrange
        odoo_employees = [
            Employee(
                id=1,
                email="employee1@example.com",
                full_name="Employee One Updated",
            ),
            Employee(
                id=2,
                email="employee2@example.com",
                full_name="Employee Two New",
            ),
        ]
        existing_users = [
            User(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
                is_active=True,
                is_superuser=False,
            ),
        ]
        self.employee_gateway.all.return_value = odoo_employees
        self.user_repository.all.return_value = existing_users

        # Act
        self.use_case.execute()

        # Assert
        self.user_repository.save_all.assert_called_once()
        saved_users = self.user_repository.save_all.call_args[0][0]
        assert len(saved_users) == 2

        # Verificar usuario existente actualizado
        existing_user = next(u for u in saved_users if u.id == 1)
        assert existing_user.email == "employee1@example.com"
        assert existing_user.full_name == "Employee One Updated"
        assert existing_user.is_active is True
        assert existing_user.is_superuser is False

        # Verificar nuevo usuario
        new_user = next(u for u in saved_users if u.id is None)
        assert new_user.email == "employee2@example.com"
        assert new_user.full_name == "Employee Two New"
        assert new_user.is_active is False
        assert new_user.is_superuser is False
