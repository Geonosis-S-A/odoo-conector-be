from jose import jwt, JWTError
from typing import Optional

from sqlalchemy import true
from app.auth.domain.models import TokenData
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastapi import HTTPException, status
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Settings:
    # Database Settings (from .env)
    DATABASE_URL: str = "postgresql://user:pass@localhost/db"
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
    COOKIE_SAMESITE: str = "lax"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


class TokenService:
    async def create_access_token(
        self, token_data: TokenData, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = {
            "user_id": token_data.user_id,
            "user_email": token_data.user_email,
            "user_name": token_data.user_name,
            "roles": token_data.roles,
        }
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    async def create_refresh_token(self, token_data: TokenData) -> str:
        to_encode = {
            "user_id": token_data.user_id,
            "user_email": token_data.user_email,
            "user_name": token_data.user_name,
            "roles": token_data.roles,
        }

        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt

    async def verify_token(self, token: str) -> TokenData:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return TokenData(
                user_id=payload["user_id"],
                user_email=payload["user_email"],
                user_name=payload["user_name"],
                roles=payload["roles"],
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def verify_password(self, hashed_password: str, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def is_active(self, user_state: bool):
        if user_state:
            return true
        return False
