from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class TokenData:
    user_id: int
    user_email: str
    user_name: str
    roles: List[int]


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
    roles: Optional[List[int]] = None


@dataclass
class NewOTPCode:
    user_id: int
    code: str
    expires_at: datetime


@dataclass
class OTPCode:
    id: int
    user_id: int
    code: str
    created_at: datetime
    expires_at: datetime
