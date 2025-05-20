import pytest
from app.users.domain.models import User as DomainUser
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.db.models import UserModel


@pytest.mark.integration
class TestSQLUserRepository:
    @pytest.fixture(autouse=True)
    def setup(self, local_db_session):
        """
        Fixture que configura el repositorio con una sesión de base de datos limpia para cada test.
        La sesión se limpia automáticamente después de cada test gracias a la fixture local_db_session.
        """
        self.db = local_db_session
        self.repository = SQLModelUserRepository(self.db)
        # Limpiar la tabla antes de cada test
        self.db.query(UserModel).delete()
        self.db.commit()

    def test_save_all_users(self):
        users = [
            DomainUser(
                id=None,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            ),
            DomainUser(
                id=None,
                email="test2@example.com",
                full_name="Test User 2",
                is_active=True,
                is_superuser=False,
            ),
        ]
        self.repository.save_all(users)
        saved_users = self.db.query(UserModel).all()
        assert len(saved_users) == 2
        assert saved_users[0].email == "test1@example.com"
        assert saved_users[1].email == "test2@example.com"
        assert all(isinstance(user, UserModel) for user in saved_users)
        assert all(hasattr(user, "id") for user in saved_users)
        assert all(hasattr(user, "email") for user in saved_users)
        assert all(hasattr(user, "full_name") for user in saved_users)

    def test_save_all_users_data_structure(self):
        users = [
            DomainUser(
                id=None,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            )
        ]
        self.repository.save_all(users)
        saved_user = self.db.query(UserModel).first()
        assert saved_user is not None
        assert isinstance(saved_user.id, int)
        assert isinstance(saved_user.email, str)
        assert isinstance(saved_user.full_name, str)
        assert isinstance(saved_user.is_active, bool)
        assert isinstance(saved_user.is_superuser, bool)

    def test_save_all_users_required_fields_not_empty(self):
        users = [
            DomainUser(
                id=None,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            )
        ]
        self.repository.save_all(users)
        saved_user = self.db.query(UserModel).first()
        assert saved_user is not None
        assert saved_user.id is not None
        assert saved_user.email != ""
        assert saved_user.full_name != ""

    def test_all_returns_domain_users(self):
        users = [
            DomainUser(
                id=None,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            ),
            DomainUser(
                id=None,
                email="test2@example.com",
                full_name="Test User 2",
                is_active=True,
                is_superuser=False,
            ),
        ]
        self.repository.save_all(users)
        result = self.repository.all()
        assert len(result) == 2
        assert all(isinstance(user, DomainUser) for user in result)
        assert all(hasattr(user, "id") for user in result)
        assert all(hasattr(user, "email") for user in result)
        assert all(hasattr(user, "full_name") for user in result)
        assert all(hasattr(user, "is_active") for user in result)
        assert all(hasattr(user, "is_superuser") for user in result)

    def test_all_users_data_structure(self):
        users = [
            DomainUser(
                id=None,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            )
        ]
        self.repository.save_all(users)
        result = self.repository.all()
        first_user = result[0]
        assert isinstance(first_user.id, int)
        assert isinstance(first_user.email, str)
        assert isinstance(first_user.full_name, str)
        assert isinstance(first_user.is_active, bool)
        assert isinstance(first_user.is_superuser, bool)

    def test_all_users_required_fields_not_empty(self):
        users = [
            DomainUser(
                id=None,
                email="test1@example.com",
                full_name="Test User 1",
                is_active=True,
                is_superuser=False,
            )
        ]
        self.repository.save_all(users)
        result = self.repository.all()
        for user in result:
            assert user.id is not None
            assert user.email != ""
            assert user.full_name != ""
