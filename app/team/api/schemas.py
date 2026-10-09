from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel


class TeamMemberView(BaseModel):
    employee_odoo_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    # None = sin permiso: la persona sólo ve sus propias horas
    level: Optional[Literal["view", "validate"]] = None
    # Vigencia del permiso (inclusive). None = sin límite en ese extremo.
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


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
    # Vigencia opcional, p. ej. para cubrir aprobaciones durante unas vacaciones.
    # Sin fechas el permiso no vence. Se ignoran con level="none".
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


class ProjectBasicView(BaseModel):
    id: int
    name: str


class TeamProjectMemberView(TeamMemberBasicView):
    # False: cargó horas en el proyecto sin tener project.assignment vigente.
    assigned: bool = True


class TeamProjectView(BaseModel):
    project: ProjectBasicView
    members: List[TeamProjectMemberView] = []
    pending_count: int = 0
    pending_previous_count: int = 0
    # Quiénes pueden aprobar las horas del proyecto (PM y gerente).
    approver_names: List[str] = []
    # Presente si el usuario ve este proyecto porque su líder le delegó la
    # aprobación (no porque lo gerencie): a quién cubre y hasta cuándo.
    covering_leader_id: Optional[int] = None
    covering_leader_name: Optional[str] = None
    covering_until: Optional[date] = None
