from abc import ABC, abstractmethod
from app.auth.domain.models import RefreshToken, UserCredentials


class UserCredentialsRepository(ABC):
    @abstractmethod
    def get_user_credentials(self, email: str) -> UserCredentials: ...


class TokenRepository(ABC):
    @abstractmethod
    def save_refresh_token(self, refresh_token: RefreshToken) -> None: ...
