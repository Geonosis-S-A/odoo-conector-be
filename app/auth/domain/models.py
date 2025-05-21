from dataclasses import dataclass
import datetime


@dataclass
class TokenData:
    user_id: int
    roles: list[str]


@dataclass
class RefreshToken:
    token: str
    user_id: int
    is_revoked: bool = False


@dataclass
class UserCredentials:
    id: int
    email: str
    password: str
    is_superuser: bool
