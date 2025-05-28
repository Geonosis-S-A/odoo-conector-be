from fastapi import HTTPException
from sqlmodel import Session, select
from app.auth.domain.models import (
    NewOTPCode,
    OTPCode,
    RefreshToken,
    UserCredentials,
)
from app.auth.domain.repositories import (
    OTPRepository,
    TokenRepository,
    UserCredentialsRepository,
    UserRepository,
)
from app.auth.infra.db.models import OTPModel, RefreshTokenModel
from app.users.infra.db.models import UserModel as UserModelDB
from datetime import datetime


class SQLModelUserCredentialsRepository(UserCredentialsRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_user_credentials(self, email: str) -> UserCredentials:
        user_model = (
            self.db.query(UserModelDB).filter(UserModelDB.email == email).first()
        )

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

    def get_user_by_id(self, user_id: int) -> UserCredentials:
        user_model = (
            self.db.query(UserModelDB).filter(UserModelDB.id == user_id).first()
        )

        if not user_model:
            raise HTTPException(status_code=404, detail="User not found")

        # Convertir UserModel a UserCredentials
        return UserCredentials(
            id=user_model.id,
            email=user_model.email,
            name=user_model.full_name,
            password=user_model.hashed_password,
            is_superuser=user_model.is_superuser,
            is_active=user_model.is_active,
        )

    def update_password(self, user_id: int, new_hashed_password: str) -> bool:
        try:
            user_model = (
                self.db.query(UserModelDB).filter(UserModelDB.id == user_id).first()
            )

            if not user_model:
                return False

            user_model.hashed_password = new_hashed_password
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False


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
        self.db.commit()

    def search_refresh_token(self, token: str) -> RefreshTokenModel:
        refresh_token_model = (
            self.db.query(RefreshTokenModel)
            .filter(RefreshTokenModel.token == token)
            .first()
        )
        if not refresh_token_model:
            raise HTTPException(status_code=404, detail="Refresh token not found")
        return refresh_token_model

    def delete_refresh_token(self, token: str) -> None:
        self.db.query(RefreshTokenModel).filter(
            RefreshTokenModel.token == token
        ).delete()
        self.db.commit()


class SQLModelOTPRepository(OTPRepository):
    def __init__(self, db: Session):
        self.db = db

    async def save(self, otp: NewOTPCode) -> None:
        otp_model = OTPModel(
            user_id=otp.user_id,
            code=otp.code,
            expires_at=otp.expires_at,
            is_used=False,
        )
        self.db.add(otp_model)
        self.db.commit()
        self.db.refresh(otp_model)

    def get_valid_otp(self, user_id: int, code: str) -> OTPCode | None:
        statement = select(OTPModel).where(
            OTPModel.user_id == user_id,
            OTPModel.code == code,
            OTPModel.is_used == False,
            OTPModel.expires_at > datetime.utcnow(),
        )

        if hasattr(self.db, "exec"):
            otp_model = self.db.exec(statement).first()
        else:
            # Fallback para sesiones de SQLAlchemy regulares
            otp_model = self.db.execute(statement).scalar_one_or_none()

        if not otp_model or otp_model.id is None:
            return None
        return OTPCode(
            id=otp_model.id,
            user_id=otp_model.user_id,
            code=otp_model.code,
            created_at=otp_model.created_at,
            expires_at=otp_model.expires_at,
        )

    def mark_otp_as_used(self, otp_id: int) -> None:
        statement = select(OTPModel).where(OTPModel.id == otp_id)

        if hasattr(self.db, "exec"):
            otp_model = self.db.exec(statement).first()
        else:
            # Fallback para sesiones de SQLAlchemy regulares
            otp_model = self.db.execute(statement).scalar_one_or_none()

        if otp_model:
            otp_model.is_used = True
            self.db.add(otp_model)
            self.db.commit()
            self.db.refresh(otp_model)
