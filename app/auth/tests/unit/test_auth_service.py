import pytest
from datetime import timedelta
from app.auth.infra.auth_service import TokenService, settings
from app.auth.domain.models import TokenData, UserCredentials
from jose import jwt
from fastapi import HTTPException
from unittest.mock import Mock


@pytest.fixture
def auth_service():
    return TokenService()


class TestAuthService:
    def test_create_access_token_success(self, auth_service: TokenService):
        """Debe crear un access token válido con los datos correctos."""
        token_data = TokenData(
            user_id=1,
            user_email="testana@example.com",
            user_name="Usuario Test",
            roles=[1, 2],
        )
        token = auth_service.create_access_token(token_data)
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["user_email"] == "testana@example.com"
        assert payload["user_name"] == "Usuario Test"
        assert payload["roles"] == [1, 2]

    def test_create_access_token_with_custom_expiration(
        self, auth_service: TokenService
    ):
        """Debe crear un access token con expiración personalizada."""
        token_data = TokenData(
            user_id=1,
            user_email="testana@example.com",
            user_name="Usuario Test",
            roles=[1, 2],
        )
        custom_expiration = timedelta(minutes=30)
        token = auth_service.create_access_token(
            token_data, expires_delta=custom_expiration
        )
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["user_email"] == "testana@example.com"
        assert payload["user_name"] == "Usuario Test"
        assert payload["roles"] == [1, 2]

    def test_create_refresh_token_success(self, auth_service: TokenService):
        """Debe crear un refresh token válido."""
        token_data = TokenData(
            user_id=1,
            user_email="testana@example.com",
            user_name="Usuario Test",
            roles=[1, 2],
        )
        token = auth_service.create_refresh_token(token_data)
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["user_email"] == "testana@example.com"
        assert payload["user_name"] == "Usuario Test"
        assert payload["roles"] == [1, 2]

    def test_verify_token_success(self, auth_service: TokenService):
        """Debe verificar un token válido y devolver el payload."""
        token_data = TokenData(
            user_id=1,
            user_email="testana@example.com",
            user_name="Usuario Test",
            roles=[1, 2],
        )
        token = auth_service.create_access_token(token_data)
        payload = auth_service.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["user_email"] == "testana@example.com"
        assert payload["user_name"] == "Usuario Test"
        assert payload["roles"] == [1, 2]

    def test_verify_token_invalid(self, auth_service: TokenService):
        """Debe lanzar una excepción si el token es inválido."""
        with pytest.raises(HTTPException):
            auth_service.verify_token("invalid_token")

    def test_refresh_access_token_success(self, auth_service: TokenService):
        """Debe refrescar el access token exitosamente."""
        # Crear un token válido para las pruebas
        token_data = TokenData(
            user_id=1,
            user_email="testana@example.com",
            user_name="Usuario Test",
            roles=[1, 2],
        )
        refresh_token = auth_service.create_refresh_token(token_data)

        # Mock para token_repository
        token_repository_mock = Mock()
        token_repository_mock.search_refresh_token.return_value = Mock(is_revoked=False)

        # Mock para user_repository - usar objeto real en lugar de Mock
        user_repository_mock = Mock()
        mock_user = UserCredentials(
            id=1,
            email="testana@example.com",
            name="Usuario Test",
            password="hashed_password",
            is_superuser=False,
            is_active=True,
            roles=[1, 2],
        )
        user_repository_mock.get_user_credentials.return_value = mock_user

        # Llamar a refresh_access_token
        new_access_token = auth_service.refresh_access_token(
            refresh_token, token_repository_mock, user_repository_mock
        )

        # Verificar que se devuelve un nuevo access token
        assert new_access_token is not None
        payload = jwt.decode(
            new_access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["user_id"] == 1
        assert payload["roles"] == [1, 2]
