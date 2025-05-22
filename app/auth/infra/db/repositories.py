from fastapi import HTTPException
from sqlmodel import Session
from app.auth.domain.models import RefreshToken, UserCredentials
from app.auth.domain.repositories import TokenRepository, UserCredentialsRepository
from app.auth.infra.db.models import RefreshTokenModel
from app.users.infra.db.models import UserModel


class SQLModelUserCredentialsRepository(UserCredentialsRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_user_credentials(self, email: str) -> UserCredentials:
        print(f"Buscando usuario con email: {email}")
        user_model = self.db.query(UserModel).filter(UserModel.email == email).first()

        print(user_model)
        if not user_model:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Convertir UserModel a UserCredentials
        return UserCredentials(
            id=user_model.id,
            email=user_model.email,
            name=user_model.full_name,
            password=user_model.hashed_password,
            is_superuser=user_model.is_superuser,
            is_active=user_model.is_active,
        )


class SQLModelTokenRepository(TokenRepository):
    def __init__(self, db: Session):
        self.db = db

    def save_refresh_token(self, refresh_token: RefreshToken) -> None:
        self.db.add(
            RefreshTokenModel(
                token=refresh_token.token,
                user_id=refresh_token.user_id,
            )
        )
