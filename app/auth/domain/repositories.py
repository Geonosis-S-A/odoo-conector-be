from abc import ABC, abstractmethod
from typing import Optional
from app.auth.domain.models import (
    NewOTPCode,
    OTPCode,
    RefreshToken,
    UserCredentials,
)
from app.auth.infra.db.models import OTPModel
from app.users.infra.db.models import UserModel


class UserCredentialsRepository(ABC):
    @abstractmethod
    def get_user_credentials(self, email: str) -> UserCredentials: ...

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> UserCredentials: ...

    @abstractmethod
    def update_password(self, user_id: int, new_hashed_password: str) -> bool: ...


class TokenRepository(ABC):
    @abstractmethod
    def save_refresh_token(self, refresh_token: RefreshToken) -> None: ...


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserModel]:
        pass

    @abstractmethod
    async def save_otp(self, otp: OTPModel) -> None:
        pass

    @abstractmethod
    async def get_valid_otp(self, user_id: int, code: str) -> Optional[OTPModel]:
        pass

    @abstractmethod
    async def update_password(self, user_id: int, hashed_password: str) -> None:
        pass

    @abstractmethod
    async def mark_otp_as_used(self, otp_id: int) -> None:
        pass


class OTPRepository(ABC):
    @abstractmethod
    async def save(self, otp: NewOTPCode) -> None:
        pass

    @abstractmethod
    async def get_valid_otp(self, user_id: int, code: str) -> Optional[OTPCode]:
        pass
