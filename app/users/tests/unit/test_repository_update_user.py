import pytest
from unittest.mock import Mock, MagicMock
from app.users.domain.models import User
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.db.models import UserModel


class TestSQLModelUserRepositoryUpdateUser:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.db_mock = Mock()
        self.repository = SQLModelUserRepository(self.db_mock)

    def test_update_user_success(self):
        """Test que verifica que update_user actualiza correctamente un usuario existente."""
        # Arrange
        user_to_update = User(
            id=1,
            email="updated@example.com",
            full_name="Updated Name",
            is_active=True,
            is_superuser=False,
        )
        
        # Mock del usuario existente en la base de datos
        existing_user_model = UserModel(
            id=1,
            email="old@example.com",
            full_name="Old Name",
            is_active=True,
            is_superuser=False,
            hashed_password="hashed_password",
        )
        
        # Configurar mocks
        self.db_mock.exec.return_value.first.return_value = existing_user_model

        # Act
        result = self.repository.update_user(user_to_update)

        # Assert
        assert result is True
        
        # Verificar que se actualizaron los campos correctos
        assert existing_user_model.email == "updated@example.com"
        assert existing_user_model.full_name == "Updated Name"
        
        # Verificar que se llamaron los métodos de la base de datos
        self.db_mock.commit.assert_called_once()
        self.db_mock.refresh.assert_called_once_with(existing_user_model)

    def test_update_user_not_found(self):
        """Test que verifica que update_user retorna False cuando el usuario no existe."""
        # Arrange
        user_to_update = User(
            id=999,
            email="nonexistent@example.com",
            full_name="Non Existent",
            is_active=True,
            is_superuser=False,
        )
        
        # Configurar mock para retornar None (usuario no encontrado)
        self.db_mock.exec.return_value.first.return_value = None

        # Act
        result = self.repository.update_user(user_to_update)

        # Assert
        assert result is False
        
        # Verificar que no se llamaron commit ni refresh
        self.db_mock.commit.assert_not_called()
        self.db_mock.refresh.assert_not_called()

    def test_update_user_preserves_password_and_state(self):
        """Test que verifica que update_user no modifica la contraseña ni el estado del usuario."""
        # Arrange
        user_to_update = User(
            id=1,
            email="updated@example.com",
            full_name="Updated Name",
            is_active=False,  # Diferente del estado actual
            is_superuser=True,  # Diferente del estado actual
        )
        
        # Mock del usuario existente con estado diferente
        existing_user_model = UserModel(
            id=1,
            email="old@example.com",
            full_name="Old Name",
            is_active=True,  # Estado actual
            is_superuser=False,  # Estado actual
            hashed_password="original_password",
        )
        
        # Configurar mocks
        self.db_mock.exec.return_value.first.return_value = existing_user_model

        # Act
        result = self.repository.update_user(user_to_update)

        # Assert
        assert result is True
        
        # Verificar que solo se actualizaron email y full_name
        assert existing_user_model.email == "updated@example.com"
        assert existing_user_model.full_name == "Updated Name"
        
        # Verificar que NO se modificaron is_active, is_superuser ni hashed_password
        assert existing_user_model.is_active is True  # Mantiene valor original
        assert existing_user_model.is_superuser is False  # Mantiene valor original
        assert existing_user_model.hashed_password == "original_password"  # Mantiene valor original

    def test_update_user_with_none_id(self):
        """Test que verifica el comportamiento cuando el usuario tiene ID None."""
        # Arrange
        user_to_update = User(
            id=None,
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )
        
        # Configurar mock para retornar None
        self.db_mock.exec.return_value.first.return_value = None

        # Act
        result = self.repository.update_user(user_to_update)

        # Assert
        assert result is False
        self.db_mock.commit.assert_not_called()
        self.db_mock.refresh.assert_not_called()

    def test_update_user_database_error_handling(self):
        """Test que verifica el manejo de errores de base de datos."""
        # Arrange
        user_to_update = User(
            id=1,
            email="updated@example.com",
            full_name="Updated Name",
            is_active=True,
            is_superuser=False,
        )
        
        existing_user_model = UserModel(
            id=1,
            email="old@example.com",
            full_name="Old Name",
            is_active=True,
            is_superuser=False,
            hashed_password="hashed_password",
        )
        
        # Configurar mocks para simular error en commit
        self.db_mock.exec.return_value.first.return_value = existing_user_model
        self.db_mock.commit.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            self.repository.update_user(user_to_update)

    def test_update_user_only_email_change(self):
        """Test que verifica actualización cuando solo cambia el email."""
        # Arrange
        user_to_update = User(
            id=1,
            email="newemail@example.com",
            full_name="Same Name",  # Mismo nombre
            is_active=True,
            is_superuser=False,
        )
        
        existing_user_model = UserModel(
            id=1,
            email="oldemail@example.com",
            full_name="Same Name",  # Mismo nombre
            is_active=True,
            is_superuser=False,
            hashed_password="hashed_password",
        )
        
        # Configurar mocks
        self.db_mock.exec.return_value.first.return_value = existing_user_model

        # Act
        result = self.repository.update_user(user_to_update)

        # Assert
        assert result is True
        assert existing_user_model.email == "newemail@example.com"
        assert existing_user_model.full_name == "Same Name"

    def test_update_user_only_name_change(self):
        """Test que verifica actualización cuando solo cambia el nombre."""
        # Arrange
        user_to_update = User(
            id=1,
            email="same@example.com",  # Mismo email
            full_name="New Name",
            is_active=True,
            is_superuser=False,
        )
        
        existing_user_model = UserModel(
            id=1,
            email="same@example.com",  # Mismo email
            full_name="Old Name",
            is_active=True,
            is_superuser=False,
            hashed_password="hashed_password",
        )
        
        # Configurar mocks
        self.db_mock.exec.return_value.first.return_value = existing_user_model

        # Act
        result = self.repository.update_user(user_to_update)

        # Assert
        assert result is True
        assert existing_user_model.email == "same@example.com"
        assert existing_user_model.full_name == "New Name" 