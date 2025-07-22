from jose import jwt, JWTError
from typing import Literal, Optional
from sqlalchemy import true
from app.auth.application.use_cases.exceptions.exceptions import (
    TokenNotFound,
    TokenRevoked,
    UserNotFound,
)
from app.auth.domain.models import TokenData
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from fastapi import HTTPException, status, Response
from passlib.context import CryptContext

from app.auth.infra.db.repositories import (
    SQLModelTokenRepository,
    SQLModelUserCredentialsRepository,
)

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Settings:
    # Database Settings (from .env)

    DIRECT_URL: Optional[str] = None

    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default_secret_key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days

    # Cookie Settings
    COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = True
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: Literal["lax"] = "lax"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


class TokenService:
    def create_access_token(
        self, token_data: TokenData, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = {
            "user_id": token_data.user_id,
            "user_email": token_data.user_email,
            "user_name": token_data.user_name,
            "roles": token_data.roles,
        }
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    def create_refresh_token(self, token_data: TokenData) -> str:
        to_encode = {
            "user_id": token_data.user_id,
            "user_email": token_data.user_email,
            "user_name": token_data.user_name,
            "roles": token_data.roles,
        }

        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def refresh_access_token(
        self,
        refresh_token: str,
        token_repository: SQLModelTokenRepository,
        user_repository: SQLModelUserCredentialsRepository,
    ) -> str:
        # Verificar token de la cookie contra BD
        refresh_token_db = token_repository.search_refresh_token(refresh_token)
        if not refresh_token_db:
            raise TokenNotFound("Invalid refresh token")
        # Si la refresh token esta vencida, tira unauthorized
        if refresh_token_db.is_revoked:
            raise TokenRevoked("Token revoked")

        # Se decodea el el token para ver si es valido
        payload = self.verify_token(refresh_token)

        # Con el payload, se verifica que el usuario siga existiendo en base de datos
        user = user_repository.get_user_credentials(payload["user_email"])
        if not user:
            raise UserNotFound("User not found")

        # Crear TokenData con los datos actuales del usuario (incluyendo roles actualizados)
        token_data = TokenData(
            user_id=user.id,
            user_email=user.email,
            user_name=user.name,
            roles=user.roles or [],
        )

        # Se crea el nuevo access token
        access_token = self.create_access_token(token_data)

        return access_token

    def logout(
        self,
        response: Response,
        token_repository: SQLModelTokenRepository,
        refresh_token: str,
    ) -> None:
        success = token_repository.delete_refresh_token(refresh_token)
        if not success:
            raise TokenNotFound("Invalid refresh token")
        response.delete_cookie(
            key=settings.COOKIE_NAME,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
        )
