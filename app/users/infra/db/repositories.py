from app.users.domain.models import User
from app.users.domain.repositories import UserRepository
from app.users.infra.db.models import UserModel


class SQLModelUserRepository(UserRepository):
    def __init__(self, db):
        self.db = db

    def save_all(self, users: list[User]):
        # TODO: Si modifia el mail, debe actualizarse tambien en base de datos.
        # TODO: Verificar que ninguno de estos exista en base de datos
        for user in users:
            user_model = UserModel(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=False,
                is_superuser=user.is_superuser,
                hashed_password="",  # TODO: Implementar hash de contraseña
            )
            self.db.add(user_model)
        self.db.commit()

    def set_password(self, user_email: str, password: str) -> User:
        user_model = (
            self.db.query(UserModel).filter(UserModel.email == user_email).first()
        )
        if user_model is None:
            raise ValueError("User not found")
        user_model.hashed_password = password
        user_model.is_active = True
        self.db.commit()
        self.db.refresh(user_model)
        return User(
            id=user_model.id,
            email=user_model.email,
            full_name=user_model.full_name,
            is_active=user_model.is_active,
            is_superuser=user_model.is_superuser,
        )

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
