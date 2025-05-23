import pytest
from datetime import timedelta
from app.auth.infra.auth_service import TokenService, settings
from app.auth.domain.models import TokenData
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
            roles=["user"],
        )
        token = auth_service.create_access_token(token_data)
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["user_email"] == "testana@example.com"
        assert payload["user_name"] == "Usuario Test"
        assert payload["roles"] == ["user"]

    def test_create_access_token_with_custom_expiration(
        self, auth_service: TokenService
    ):
        """Debe crear un access token con expiración personalizada."""
        token_data = TokenData(
            user_id=1,
            user_email="testana@example.com",
            user_name="Usuario Test",
            roles=["user"],
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
        assert payload["roles"] == ["user"]

    def test_create_refresh_token_success(self, auth_service: TokenService):
        """Debe crear un refresh token válido."""
        token_data = TokenData(
            user_id=1,
            user_email="testana@example.com",
            user_name="Usuario Test",
            roles=["user"],
        )
        token = auth_service.create_refresh_token(token_data)
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["user_email"] == "testana@example.com"
        assert payload["user_name"] == "Usuario Test"
        assert payload["roles"] == ["user"]

    def test_verify_token_success(self, auth_service: TokenService):
        """Debe decodificar correctamente un token válido."""
        token = jwt.encode(
            {
                "user_id": 1,
                "user_email": "testana@example.com",
                "user_name": "Usuario Test",
                "roles": ["user"],
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        result = auth_service.verify_token(token)
        assert result["user_id"] == 1
        assert result["user_email"] == "testana@example.com"
        assert result["user_name"] == "Usuario Test"
        assert result["roles"] == ["user"]

    def test_verify_token_invalid(self, auth_service: TokenService):
        """Debe lanzar HTTPException si el token es inválido."""
        invalid_token = "invalid.token.string"
        with pytest.raises(HTTPException) as excinfo:
            auth_service.verify_token(invalid_token)
        assert excinfo.value.status_code == 401
        assert "Could not validate credentials" in excinfo.value.detail
