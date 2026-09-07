from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel


class TeamMemberPermissionModel(SQLModel, table=True):
    __tablename__ = "teammemberpermissionmodel"
    __table_args__ = (
        CheckConstraint(
            "level IN ('view', 'validate')",
            name="ck_teammemberpermissionmodel_level",
        ),
        UniqueConstraint(
            "leader_employee_odoo_id",
            "member_employee_odoo_id",
            name="uq_teammemberpermission_leader_member",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    leader_employee_odoo_id: int = Field(index=True)
    member_employee_odoo_id: int = Field(index=True)
    level: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
