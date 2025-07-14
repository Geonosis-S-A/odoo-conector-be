from dataclasses import dataclass

from app.auth.domain.models import TokenData


@dataclass
class LoginResponse:
    access_token: str
    refresh_token: str
    user: TokenData
