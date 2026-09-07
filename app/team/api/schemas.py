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


class TeamMemberBasicView(BaseModel):
    employee_odoo_id: int
    name: Optional[str] = None
    email: Optional[str] = None


class MyTeamAccessView(BaseModel):
    """Lo que el usuario logueado puede hacer con "su equipo".

    - can_view_team=False               -> sin acceso: sólo ve sus horas
    - can_view_team=True, validate=False -> ve las horas del equipo, sin validar
    - can_validate_team=True (o is_leader) -> ve y valida
    """

    is_leader: bool
    can_view_team: bool
    can_validate_team: bool
    members: List[TeamMemberBasicView] = []


class SetPermissionRequest(BaseModel):
    # "none" elimina el permiso (la persona vuelve a ver sólo sus horas)
    level: Literal["view", "validate", "none"]
