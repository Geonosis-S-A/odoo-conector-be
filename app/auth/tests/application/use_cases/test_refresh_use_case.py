import pytest
from unittest.mock import Mock
from app.auth.application.use_cases.refresh import RefreshUseCase
from app.auth.infra.auth_service import TokenService
from app.auth.infra.db.repositories import (
    SQLModelTokenRepository,
    SQLModelUserCredentialsRepository,
)
from fastapi import HTTPException


def test_refresh_access_token_success():
    # Arrange
    refresh_token = "valid_refresh_token"
    expected_access_token = "new_access_token"

    token_repository = Mock(spec=SQLModelTokenRepository)
    user_repository = Mock(spec=SQLModelUserCredentialsRepository)

    # Mock TokenService
    mock_token_service = Mock(spec=TokenService)
    mock_token_service.refresh_access_token.return_value = expected_access_token

    use_case = RefreshUseCase()
    use_case.auth_service = mock_token_service  # Inyectamos el mock

    # Act
    access_token = use_case.execute(refresh_token, token_repository, user_repository)

    # Assert
    assert access_token == expected_access_token
    mock_token_service.refresh_access_token.assert_called_once_with(
        refresh_token, token_repository, user_repository
    )


def test_refresh_access_token_invalid_token():
    # Arrange
    refresh_token = "invalid_refresh_token"
    token_repository = Mock(spec=SQLModelTokenRepository)
    user_repository = Mock(spec=SQLModelUserCredentialsRepository)

    # Mock TokenService
    mock_token_service = Mock(spec=TokenService)
    mock_token_service.refresh_access_token.side_effect = HTTPException(
        status_code=401, detail="Invalid refresh token"
    )

    use_case = RefreshUseCase()
    use_case.auth_service = mock_token_service  # Inyectamos el mock

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        use_case.execute(refresh_token, token_repository, user_repository)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"
    mock_token_service.refresh_access_token.assert_called_once_with(
        refresh_token, token_repository, user_repository
    )
