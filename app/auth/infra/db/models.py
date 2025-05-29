from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING

# Importación condicional para evitar circular imports
if TYPE_CHECKING:
    from app.users.infra.db.models import UserModel


class RefreshTokenModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="usermodel.id")
    is_revoked: bool = Field(default=False)


class OTPModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="usermodel.id")
    code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_used: bool = Field(default=False)
    # Usamos string para la referencia hacia adelante
    user: Optional["UserModel"] = Relationship(back_populates="otps")
