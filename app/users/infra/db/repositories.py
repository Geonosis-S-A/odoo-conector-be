from app.users.domain.models import User
from app.users.domain.repositories import UserRepository
from app.users.infra.db.models import UserModel


class SQLModelUserRepository(UserRepository):
    def __init__(self, db):
        self.db = db

    def save_all(self, users: list[User]):
        for user in users:
            user_model = UserModel(
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                hashed_password="",  # TODO: Implementar hash de contraseña
            )
            self.db.add(user_model)
        self.db.commit()

    def all(self) -> list[User]:
        users = self.db.query(UserModel).all()
        return [
            User(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
            )
            for user in users
        ]
