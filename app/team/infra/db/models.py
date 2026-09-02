from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import CheckConstraint, String
from sqlmodel import Field, Relationship, SQLModel


class TeamModel(SQLModel, table=True):
    __tablename__ = "teammodel"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    members: List["TeamMemberModel"] = Relationship(back_populates="team")


class TeamMemberModel(SQLModel, table=True):
    __tablename__ = "teammembermodel"
    __table_args__ = (
        CheckConstraint(
            "role IN ('leader', 'pm', 'sub_leader', 'member')",
            name="ck_teammembermodel_role",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teammodel.id", index=True)
    employee_odoo_id: int = Field(index=True)
    role: str = Field(sa_type=String)
    can_validate: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    team: Optional["TeamModel"] = Relationship(back_populates="members")
