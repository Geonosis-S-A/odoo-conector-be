import pytest
from unittest.mock import Mock
from app.auth.application.use_cases.register import RegisterUseCase

from app.auth.infra.auth_service import TokenService
from app.users.domain.models import User
from app.users.domain.repositories import UserRepository


def test_register_user_success():
    # Arrange
    user_repository = Mock(spec=UserRepository)
    auth_service = Mock(spec=TokenService)
    hashed_password = "hashed_securepassword"
    auth_service.hash_password.return_value = hashed_password
    user_repository.set_password.return_value = User(
        id=1,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )

    register_use_case = RegisterUseCase(user_repository, auth_service)

    # Act
    user = register_use_case.execute("test@example.com", "securepassword")

    # Assert
    assert user.id == 1
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.is_superuser is False
    user_repository.set_password.assert_called_once_with(
        "test@example.com", hashed_password
    )
