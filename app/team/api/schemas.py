from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.team.domain.models import TeamRole


class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    employee_odoo_id: int
    role: TeamRole
    can_validate: bool
    created_at: Optional[datetime] = None


class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    members: List[TeamMemberResponse] = []


class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None


class AddMemberRequest(BaseModel):
    employee_odoo_id: int
    role: TeamRole
    can_validate: bool = False


class UpdateMemberRequest(BaseModel):
    role: TeamRole
    can_validate: bool = False
