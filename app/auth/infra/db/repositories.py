from fastapi import HTTPException
from sqlmodel import Session
from app.auth.domain.models import RefreshToken, UserCredentials
from app.auth.domain.repositories import TokenRepository, UserCredentialsRepository
from app.auth.infra.db.models import RefreshTokenModel


class SQLModelUserCredentialsRepository(UserCredentialsRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_user_credentials(self, email: str) -> UserCredentials:
        user_credentials = self.db.query(UserCredentials).filter(UserCredentials.email == email).first())

        if not user_credentials:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return user_credentials

class SQLModelTokenRepository(TokenRepository):
    def __init__(self, db: Session):
        self.db = db

    def save_refresh_token(self, refresh_token: RefreshToken) -> None:
        self.db.add(RefreshTokenModel(
            token=refresh_token.token,
            user_id=refresh_token.user_id,
        ))