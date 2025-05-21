import pytest
from unittest.mock import Mock
from datetime import timedelta
from app.auth.infra.auth_service import TokenService, settings
from app.auth.domain.models import TokenData
from jose import jwt, JWTError
from fastapi import HTTPException
import pytest_asyncio


@pytest_asyncio.fixture
async def auth_service():
    return TokenService()


class TestAuthService:
    @pytest.mark.asyncio
    async def test_get_access_token_success(self, auth_service: TokenService):
        # Arrange
        token_data = TokenData(user_id=1, roles=["user"])

        # Act
        token = await auth_service.create_access_token(token_data)

        # Assert
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["roles"] == ["user"]

    @pytest.mark.asyncio
    async def test_get_access_token_with_custom_expiration(
        self, auth_service: TokenService
    ):
        # Arrange
        token_data = TokenData(user_id=1, roles=["user"])
        custom_expiration = timedelta(minutes=30)

        # Act
        token = await auth_service.create_access_token(
            token_data, expires_delta=custom_expiration
        )

        # Assert
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["roles"] == ["user"]

    @pytest.mark.asyncio
    async def test_get_refresh_token_success(self, auth_service: TokenService):
        # Arrange
        token_data = TokenData(user_id=1, roles=["user"])

        # Act
        token = await auth_service.create_refresh_token(token_data)

        # Assert
        assert token is not None
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["user_id"] == 1
        assert payload["roles"] == ["user"]

    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_service: TokenService):
        # Arrange
        token_data = TokenData(user_id=1, roles=["user"])
        token_data = jwt.encode(
            {"user_id": 1, "roles": ["user"]},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Act
        result = await auth_service.verify_token(token_data)

        # Assert
        assert result.user_id == 1
        assert result.roles == ["user"]

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, auth_service: TokenService):
        # Arrange
        invalid_token = "invalid.token.string"

        # Act & Assert
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.verify_token(invalid_token)
        assert excinfo.value.status_code == 401
        assert "Could not validate credentials" in excinfo.value.detail
