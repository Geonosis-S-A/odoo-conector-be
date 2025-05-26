from abc import ABC, abstractmethod
from app.auth.domain.models import RefreshToken, UserCredentials


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
