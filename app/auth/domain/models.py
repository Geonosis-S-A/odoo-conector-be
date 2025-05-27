from dataclasses import dataclass
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime

from app.users.infra.db.models import UserModel  # Usar el modelo real de la base de datos


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


class OTPModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_used: bool = Field(default=False)
    user: Optional["UserModel"] = Relationship(back_populates="otps")
