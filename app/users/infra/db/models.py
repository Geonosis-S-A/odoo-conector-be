from datetime import datetime, UTC
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr
from sqlalchemy import event

# Importación condicional para evitar circular imports
if TYPE_CHECKING:
    from app.auth.infra.db.models import OTPModel


class UserBaseModel(SQLModel):
    """Base model for User with common fields"""

    email: EmailStr = Field(unique=True, index=True)
    full_name: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class UserModel(UserBaseModel, table=True):
    """User model for database"""

    id: Optional[int] = Field(primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Usamos string para la referencia hacia adelante
    otps: List["OTPModel"] = Relationship(back_populates="user")


@event.listens_for(UserModel, "before_update")
def update_timestamp(mapper, connection, target):
    target.updated_at = datetime.now(UTC)
