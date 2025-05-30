import pytest
from unittest.mock import Mock
from app.users.domain.models import Employee, User
from app.users.application.use_cases.sync_user_changes import SyncUserChangesUseCase


class TestSyncUserChangesUseCase:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.employee_gateway = Mock()
        self.user_repository = Mock()
        self.use_case = SyncUserChangesUseCase(
            employee_gateway=self.employee_gateway,
            user_repository=self.user_repository,
        )

    def test_sync_updates_existing_users_with_changes(self):
        """Test que verifica que se actualicen usuarios existentes cuando hay cambios en email o nombre."""
        # Arrange
        odoo_employees = [
            Employee(
                id=1,
                email="updated@example.com",
                full_name="Updated Name",
            ),
            Employee(
                id=2,
                email="employee2@example.com",
                full_name="Employee Two Updated",
            ),
        ]
        existing_users = [
            User(
                id=1,
                email="old@example.com",
                full_name="Old Name",
                is_active=True,
                is_superuser=False,
            ),
            User(
                id=2,
                email="employee2@example.com",
                full_name="Employee Two",
                is_active=False,
                is_superuser=True,
            ),
        ]
        
        self.employee_gateway.all.return_value = odoo_employees
        self.user_repository.all.return_value = existing_users
        self.user_repository.update_user.return_value = True

        # Act
        result = self.use_case.execute()

        # Assert
        assert len(result["updated"]) == 2
        assert len(result["unchanged"]) == 0
        
        # Verificar que se llamó update_user para ambos usuarios
        assert self.user_repository.update_user.call_count == 2
        
        # Verificar que los usuarios actualizados mantienen su estado original
        updated_users = result["updated"]
        
        # Usuario 1: cambió email y nombre
        user1 = next(u for u in updated_users if u.id == 1)
        assert user1.email == "updated@example.com"
        assert user1.full_name == "Updated Name"
        assert user1.is_active is True  # Mantiene estado original
        assert user1.is_superuser is False  # Mantiene estado original
        
        # Usuario 2: cambió solo nombre
        user2 = next(u for u in updated_users if u.id == 2)
        assert user2.email == "employee2@example.com"
        assert user2.full_name == "Employee Two Updated"
        assert user2.is_active is False  # Mantiene estado original
        assert user2.is_superuser is True  # Mantiene estado original

    def test_sync_keeps_unchanged_users(self):
        """Test que verifica que usuarios sin cambios se mantengan en la lista de unchanged."""
        # Arrange
        odoo_employees = [
            Employee(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
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
        result = self.use_case.execute()

        # Assert
        assert len(result["updated"]) == 0
        assert len(result["unchanged"]) == 1
        
        # Verificar que no se llamó update_user
        self.user_repository.update_user.assert_not_called()
        
        # Verificar que el usuario sin cambios está en unchanged
        unchanged_user = result["unchanged"][0]
        assert unchanged_user.id == 1
        assert unchanged_user.email == "employee1@example.com"
        assert unchanged_user.full_name == "Employee One"

    def test_sync_handles_users_not_in_odoo(self):
        """Test que verifica que usuarios que no existen en Odoo se mantengan sin cambios."""
        # Arrange
        odoo_employees = []  # No hay empleados en Odoo
        existing_users = [
            User(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
                is_active=True,
                is_superuser=False,
            ),
            User(
                id=2,
                email="employee2@example.com",
                full_name="Employee Two",
                is_active=False,
                is_superuser=True,
            ),
        ]
        
        self.employee_gateway.all.return_value = odoo_employees
        self.user_repository.all.return_value = existing_users

        # Act
        result = self.use_case.execute()

        # Assert
        assert len(result["updated"]) == 0
        assert len(result["unchanged"]) == 2
        
        # Verificar que no se llamó update_user
        self.user_repository.update_user.assert_not_called()
        
        # Verificar que ambos usuarios están en unchanged
        unchanged_users = result["unchanged"]
        assert len(unchanged_users) == 2
        assert all(user.id in [1, 2] for user in unchanged_users)

    def test_sync_mixed_scenario(self):
        """Test que verifica un escenario mixto con usuarios actualizados, sin cambios y no en Odoo."""
        # Arrange
        odoo_employees = [
            Employee(
                id=1,
                email="updated@example.com",
                full_name="Updated Name",
            ),
            Employee(
                id=2,
                email="employee2@example.com",
                full_name="Employee Two",
            ),
            # Usuario 3 no está en Odoo
        ]
        existing_users = [
            User(
                id=1,
                email="old@example.com",
                full_name="Old Name",
                is_active=True,
                is_superuser=False,
            ),
            User(
                id=2,
                email="employee2@example.com",
                full_name="Employee Two",
                is_active=False,
                is_superuser=True,
            ),
            User(
                id=3,
                email="employee3@example.com",
                full_name="Employee Three",
                is_active=True,
                is_superuser=False,
            ),
        ]
        
        self.employee_gateway.all.return_value = odoo_employees
        self.user_repository.all.return_value = existing_users
        self.user_repository.update_user.return_value = True

        # Act
        result = self.use_case.execute()

        # Assert
        assert len(result["updated"]) == 1  # Solo usuario 1
        assert len(result["unchanged"]) == 2  # Usuarios 2 y 3
        
        # Verificar que se llamó update_user solo una vez
        self.user_repository.update_user.assert_called_once()
        
        # Verificar usuario actualizado
        updated_user = result["updated"][0]
        assert updated_user.id == 1
        assert updated_user.email == "updated@example.com"
        assert updated_user.full_name == "Updated Name"
        
        # Verificar usuarios sin cambios
        unchanged_users = result["unchanged"]
        unchanged_ids = [user.id for user in unchanged_users]
        assert 2 in unchanged_ids
        assert 3 in unchanged_ids

    def test_sync_handles_users_with_none_id(self):
        """Test que verifica que usuarios con ID None se manejen correctamente."""
        # Arrange
        odoo_employees = [
            Employee(
                id=1,
                email="employee1@example.com",
                full_name="Employee One",
            ),
        ]
        existing_users = [
            User(
                id=None,  # Usuario sin ID
                email="no-id@example.com",
                full_name="No ID User",
                is_active=True,
                is_superuser=False,
            ),
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
        result = self.use_case.execute()

        # Assert
        # Solo debe procesar el usuario con ID válido
        assert len(result["updated"]) == 0
        assert len(result["unchanged"]) == 1
        
        # Verificar que el usuario procesado es el que tiene ID
        unchanged_user = result["unchanged"][0]
        assert unchanged_user.id == 1

    def test_sync_empty_lists(self):
        """Test que verifica el comportamiento con listas vacías."""
        # Arrange
        self.employee_gateway.all.return_value = []
        self.user_repository.all.return_value = []

        # Act
        result = self.use_case.execute()

        # Assert
        assert len(result["updated"]) == 0
        assert len(result["unchanged"]) == 0
        self.user_repository.update_user.assert_not_called() 