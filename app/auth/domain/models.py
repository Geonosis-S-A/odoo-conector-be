from dataclasses import dataclass


@dataclass
class TokenData:
    user_id: int
    user_email: str
    user_name: str
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
    name: str
    is_superuser: bool
    is_active: bool
