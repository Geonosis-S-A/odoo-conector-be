from typing import List, Literal, Optional

from pydantic import BaseModel


class TeamMemberView(BaseModel):
    employee_odoo_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    # None = sin permiso: la persona sólo ve sus propias horas
    level: Optional[Literal["view", "validate"]] = None


class TeamView(BaseModel):
    leader_employee_odoo_id: int
    members: List[TeamMemberView] = []


class SetPermissionRequest(BaseModel):
    # "none" elimina el permiso (la persona vuelve a ver sólo sus horas)
    level: Literal["view", "validate", "none"]
