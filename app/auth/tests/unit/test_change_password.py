import pytest
from unittest.mock import Mock
from fastapi import HTTPException
from app.auth.application.use_cases.change_password import ChangePasswordUseCase
from app.auth.domain.models import UserCredentials


class TestChangePasswordUseCase:
    @pytest.fixture
    def mock_auth_service(self):
        """Fixture que proporciona un servicio de autenticación mockeado."""
        return Mock()

    @pytest.fixture
    def mock_user_repository(self):
        """Fixture que proporciona un repositorio de usuarios mockeado."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_auth_service, mock_user_repository):
        """Fixture que proporciona el caso de uso con dependencias mockeadas."""
        return ChangePasswordUseCase(mock_auth_service, mock_user_repository)

    def test_change_password_success(self, use_case, mock_auth_service, mock_user_repository):
        """Test que verifica el cambio exitoso de contraseña."""
        # Arrange
        user_id = 1
        current_password = "old_password"
        new_password = "new_password"
        
        mock_user_credentials = UserCredentials(
            id=user_id,
            email="test@example.com",
            name="Test User",
            password="hashed_old_password",
            is_active=True,
            is_superuser=False,
        )

        mock_user_repository.get_user_by_id.return_value = mock_user_credentials
        mock_auth_service.is_active.return_value = True
        mock_auth_service.verify_password.side_effect = [True, False]  # current correct, new different
        mock_auth_service.hash_password.return_value = "hashed_new_password"
        mock_user_repository.update_password.return_value = True

        # Act
        result = use_case.execute(user_id, current_password, new_password)

        # Assert
        assert result is True
        mock_user_repository.get_user_by_id.assert_called_once_with(user_id)
        mock_auth_service.verify_password.assert_any_call("hashed_old_password", current_password)
        mock_auth_service.hash_password.assert_called_once_with(new_password)
        mock_user_repository.update_password.assert_called_once_with(user_id, "hashed_new_password")

    def test_change_password_user_not_found(self, use_case, mock_user_repository):
        """Test que verifica el error cuando el usuario no existe."""
        # Arrange
        user_id = 999
        current_password = "old_password"
        new_password = "new_password"
        
        mock_user_repository.get_user_by_id.side_effect = HTTPException(
            status_code=404, detail="User not found"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            use_case.execute(user_id, current_password, new_password)
        
        assert exc_info.value.status_code == 404
        assert "Usuario no encontrado" in str(exc_info.value.detail)

    def test_change_password_user_inactive(self, use_case, mock_auth_service, mock_user_repository):
        """Test que verifica el error cuando el usuario está inactivo."""
        # Arrange
        user_id = 1
        current_password = "old_password"
        new_password = "new_password"
        
        mock_user_credentials = UserCredentials(
            id=user_id,
            email="test@example.com",
            name="Test User",
            password="hashed_old_password",
            is_active=False,  # Usuario inactivo
            is_superuser=False,
        )

        mock_user_repository.get_user_by_id.return_value = mock_user_credentials
        mock_auth_service.is_active.return_value = False

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            use_case.execute(user_id, current_password, new_password)
        
        assert exc_info.value.status_code == 401
        assert "Usuario inactivo" in str(exc_info.value.detail)

    def test_change_password_incorrect_current_password(self, use_case, mock_auth_service, mock_user_repository):
        """Test que verifica el error cuando la contraseña actual es incorrecta."""
        # Arrange
        user_id = 1
        current_password = "wrong_password"
        new_password = "new_password"
        
        mock_user_credentials = UserCredentials(
            id=user_id,
            email="test@example.com",
            name="Test User",
            password="hashed_old_password",
            is_active=True,
            is_superuser=False,
        )

        mock_user_repository.get_user_by_id.return_value = mock_user_credentials
        mock_auth_service.is_active.return_value = True
        mock_auth_service.verify_password.return_value = False  # Contraseña incorrecta

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            use_case.execute(user_id, current_password, new_password)
        
        assert exc_info.value.status_code == 401
        assert "Contraseña actual incorrecta" in str(exc_info.value.detail)

    def test_change_password_same_as_current(self, use_case, mock_auth_service, mock_user_repository):
        """Test que verifica el error cuando la nueva contraseña es igual a la actual."""
        # Arrange
        user_id = 1
        current_password = "same_password"
        new_password = "same_password"
        
        mock_user_credentials = UserCredentials(
            id=user_id,
            email="test@example.com",
            name="Test User",
            password="hashed_password",
            is_active=True,
            is_superuser=False,
        )

        mock_user_repository.get_user_by_id.return_value = mock_user_credentials
        mock_auth_service.is_active.return_value = True
        mock_auth_service.verify_password.return_value = True  # Ambas contraseñas son iguales

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            use_case.execute(user_id, current_password, new_password)
        
        assert exc_info.value.status_code == 400
        assert "La nueva contraseña debe ser diferente a la actual" in str(exc_info.value.detail)

    def test_change_password_update_fails(self, use_case, mock_auth_service, mock_user_repository):
        """Test que verifica el error cuando falla la actualización en la base de datos."""
        # Arrange
        user_id = 1
        current_password = "old_password"
        new_password = "new_password"
        
        mock_user_credentials = UserCredentials(
            id=user_id,
            email="test@example.com",
            name="Test User",
            password="hashed_old_password",
            is_active=True,
            is_superuser=False,
        )

        mock_user_repository.get_user_by_id.return_value = mock_user_credentials
        mock_auth_service.is_active.return_value = True
        mock_auth_service.verify_password.side_effect = [True, False]  # current correct, new different
        mock_auth_service.hash_password.return_value = "hashed_new_password"
        mock_user_repository.update_password.return_value = False  # Falla la actualización

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            use_case.execute(user_id, current_password, new_password)
        
        assert exc_info.value.status_code == 500
        assert "Error al actualizar la contraseña" in str(exc_info.value.detail) 