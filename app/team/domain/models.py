from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Optional, List


class TeamRole(StrEnum):
    leader = "leader"
    pm = "pm"
    sub_leader = "sub_leader"
    member = "member"


ROLES_WITH_VALIDATE = {TeamRole.leader, TeamRole.pm}
ROLES_WITH_TEAM_VIEW = {TeamRole.leader, TeamRole.pm, TeamRole.sub_leader}


@dataclass
class TeamMember:
    id: Optional[int]
    team_id: int
    employee_odoo_id: int
    role: TeamRole
    can_validate: bool
    created_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        team_id: int,
        employee_odoo_id: int,
        role: TeamRole,
        can_validate: bool = False,
    ) -> "TeamMember":
        effective_can_validate = cls._resolve_can_validate(role, can_validate)
        return cls(
            id=None,
            team_id=team_id,
            employee_odoo_id=employee_odoo_id,
            role=role,
            can_validate=effective_can_validate,
        )

    @staticmethod
    def _resolve_can_validate(role: TeamRole, requested: bool) -> bool:
        if role in ROLES_WITH_VALIDATE:
            return True
        if role == TeamRole.member:
            return False
        return requested  # sub_leader: lo que pida el líder


@dataclass
class Team:
    id: Optional[int]
    name: str
    description: Optional[str]
    created_at: Optional[datetime] = None
    members: List[TeamMember] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, description: Optional[str] = None) -> "Team":
        return cls(id=None, name=name, description=description)
