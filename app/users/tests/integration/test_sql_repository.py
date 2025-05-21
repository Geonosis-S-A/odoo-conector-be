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

    def test_set_password_updates_hashed_password(self):
        # Crear y guardar un usuario
        user = DomainUser(
            id=None,
            email="setpass@example.com",
            full_name="Set Pass User",
            is_active=True,
            is_superuser=False,
        )
        self.repository.save_all([user])
        saved_user = (
            self.db.query(UserModel).filter_by(email="setpass@example.com").first()
        )
        assert saved_user is not None
        # Cambiar la contraseña
        new_password = "new_hashed_password_123"
        updated_user = self.repository.set_password(saved_user.id, new_password)
        # Verificar en la base de datos
        refreshed_user = self.db.query(UserModel).filter_by(id=saved_user.id).first()
        assert refreshed_user.hashed_password == new_password
        # Verificar que el método retorna el dominio correcto
        assert updated_user.id == saved_user.id
        assert updated_user.email == saved_user.email
        assert updated_user.full_name == saved_user.full_name
        assert updated_user.is_active == saved_user.is_active
        assert updated_user.is_superuser == saved_user.is_superuser

    def test_set_password_user_not_found(self):
        # Intentar cambiar la contraseña de un usuario inexistente
        with pytest.raises(ValueError, match="User not found"):
            self.repository.set_password(99999, "irrelevant")
