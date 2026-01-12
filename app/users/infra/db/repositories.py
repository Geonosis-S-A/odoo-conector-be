from sqlmodel import select
from app.users.domain.models import User
from app.users.domain.repositories import UserRepository
from app.users.infra.db.models import UserModel


class SQLModelUserRepository(UserRepository):
    def __init__(self, db):
        self.db = db

    def save_all(self, users: list[User]):
        """Deprecated: Use save_all instead"""
        for user in users:
            user_model = UserModel(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=False,
                is_superuser=user.is_superuser,
                hashed_password="",
                roles=user.roles,
            )
            self.db.add(user_model)
        self.db.commit()

    def set_password(self, user_email: str, password: str) -> User:
        statement = select(UserModel).where(UserModel.email == user_email)
        user_model = self.db.exec(statement).first()
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
            roles=user_model.roles,
        )

    def all(self) -> list[User]:
        statement = select(UserModel)
        users = self.db.exec(statement).all()
        return [
            User(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                roles=user.roles,
            )
            for user in users
        ]

    def save(self, user: User) -> None:
        user_model = UserModel(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            hashed_password="",
            roles=user.roles,
        )
        self.db.add(user_model)
        self.db.commit()
        self.db.refresh(user_model)

    def get_by_email(self, email: str) -> User | None:
        statement = select(UserModel).where(UserModel.email == email)
        user_model = self.db.exec(statement).first()
        if user_model is None:
            return None
        return User(
            id=user_model.id,
            email=user_model.email,
            full_name=user_model.full_name,
            is_active=user_model.is_active,
            is_superuser=user_model.is_superuser,
            roles=user_model.roles,
        )

    def update_password(self, user_id: int, new_hashed_password: str) -> bool:
        statement = select(UserModel).where(UserModel.id == user_id)
        user_model = self.db.exec(statement).first()
        if user_model is None:
            return False
        user_model.hashed_password = new_hashed_password
        user_model.is_active = True
        self.db.commit()
        self.db.refresh(user_model)
        return True

    def update_user(self, user: User) -> bool:
        """Actualiza los datos de un usuario existente."""
        statement = select(UserModel).where(UserModel.id == user.id)
        user_model = self.db.exec(statement).first()
        if user_model is None:
            return False

        # Actualizar solo los campos que pueden cambiar desde Odoo
        user_model.email = user.email
        user_model.full_name = user.full_name
        user_model.roles = user.roles
        # Mantener el estado actual de is_active e is_superuser

        self.db.commit()
        self.db.refresh(user_model)
        return True

    def get_by_id(self, user_id: int) -> User | None:
        """Obtiene un usuario por su ID."""
        statement = select(UserModel).where(UserModel.id == user_id)
        user_model = self.db.exec(statement).first()
        if user_model is None:
            return None
        return User(
            id=user_model.id,
            email=user_model.email,
            full_name=user_model.full_name,
            is_active=user_model.is_active,
            is_superuser=user_model.is_superuser,
            roles=user_model.roles,
        )
