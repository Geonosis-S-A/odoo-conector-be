import pytest
from app.users.domain.models import User
from app.users.infra.db.repositories import SQLModelUserRepository
from app.shared.infra.db.session import SessionLocal


@pytest.mark.integration  # type: ignore[attr-defined]
class TestSQLUserRepository:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.db = SessionLocal()
        self.repository = SQLModelUserRepository(self.db)
        # Limpiamos la base de datos antes de cada test
        self.db.query(User).delete()
        self.db.commit()

    def teardown_method(self):
        # Limpiamos la base de datos después de cada test
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_save_all_users(self):
        # Arrange
        users = [
            User(
                id=1,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            ),
            User(
                id=2,
                email="test2@example.com",
                full_name="Test User 2",
                is_active=True,
                is_superuser=False,
            ),
        ]

        # Act
        self.repository.save_all(users)

        # Assert
        saved_users = self.db.query(User).all()
        assert len(saved_users) == 2
        assert saved_users[0].email == "test1@example.com"
        assert saved_users[1].email == "test2@example.com"
        assert all(isinstance(user, User) for user in saved_users)
        assert all(hasattr(user, "id") for user in saved_users)
        assert all(hasattr(user, "email") for user in saved_users)
        assert all(hasattr(user, "full_name") for user in saved_users)

    def test_save_all_users_data_structure(self):
        # Arrange
        users = [
            User(
                id=1,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            )
        ]

        # Act
        self.repository.save_all(users)

        # Assert
        saved_user = self.db.query(User).first()
        assert saved_user is not None
        assert isinstance(saved_user.id, int)
        assert isinstance(saved_user.email, str)
        assert isinstance(saved_user.full_name, str)
        assert isinstance(saved_user.is_active, bool)
        assert isinstance(saved_user.is_superuser, bool)

    def test_save_all_users_required_fields_not_empty(self):
        # Arrange
        users = [
            User(
                id=1,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            )
        ]

        # Act
        self.repository.save_all(users)

        # Assert
        saved_user = self.db.query(User).first()
        assert saved_user is not None, "El usuario no debería ser None"
        assert saved_user.id is not None
        assert saved_user.email != ""
        assert saved_user.full_name != ""
