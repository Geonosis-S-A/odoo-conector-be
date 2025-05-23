from sqlmodel import SQLModel, Field
from typing import Optional


class RefreshTokenModel(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="users.id")
    is_revoked: bool = Field(default=False)
