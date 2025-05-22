import pytest
from app.users.domain.models import User


class TestUserDomain:
    def test_create_user_with_valid_data(self):
        user = User(
            id=None,
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_equality(self):
        user1 = User(
            id=1,
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )
        user2 = User(
            id=1,
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )
        assert user1 == user2

    def test_user_inequality(self):
        user1 = User(
            id=1,
            email="test1@example.com",
            full_name="Test User 1",
            is_active=True,
            is_superuser=False,
        )
        user2 = User(
            id=2,
            email="test2@example.com",
            full_name="Test User 2",
            is_active=True,
            is_superuser=False,
        )
        assert user1 != user2
