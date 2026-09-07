from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles, user_has_role
from app.team.api.dependencies import (
    get_permission_repository,
    get_team_access_service,
)
from app.team.api.schemas import (
    MyTeamAccessView,
    SetPermissionRequest,
    TeamMemberBasicView,
    TeamMemberView,
    TeamView,
)
from app.team.application.team_access import TeamAccessService, TeamMemberInfo
from app.team.application.use_cases.get_team import GetTeamUseCase
from app.team.application.use_cases.set_member_permission import (
    SetMemberPermissionUseCase,
)
from app.team.domain.models import PermissionLevel
from app.team.infra.db.repositories import SQLModelTeamPermissionRepository

router = APIRouter(prefix="/teams", tags=["teams"])


def _member_to_view(m: TeamMemberInfo) -> TeamMemberView:
    return TeamMemberView(
        employee_odoo_id=m.employee_odoo_id,
        name=m.name,
        email=m.email,
        level=m.level.value if m.level is not None else None,
    )


def _team_to_view(leader_id: int, members: List[TeamMemberInfo]) -> TeamView:
    return TeamView(
        leader_employee_odoo_id=leader_id,
        members=[_member_to_view(m) for m in members],
    )


def _require_admin(current_user: dict) -> None:
    if not user_has_role(current_user.get("roles"), Roles.approver):
        raise HTTPException(
            status_code=403, detail="Se requiere rol de administrador"
        )


def _get_team_or_error(
    access: TeamAccessService,
    repo: SQLModelTeamPermissionRepository,
    leader_id: int,
    *,
    not_found_status: int,
) -> List[TeamMemberInfo]:
    members = GetTeamUseCase(access, repo).execute(leader_id)
    if not members:
        raise HTTPException(
            status_code=not_found_status,
            detail=f"El empleado {leader_id} no lidera un equipo en Odoo",
        )
    return members


def _apply_permission(
    access: TeamAccessService,
    repo: SQLModelTeamPermissionRepository,
    leader_id: int,
    member_id: int,
    level_str: str,
) -> TeamMemberView:
    level = None if level_str == "none" else PermissionLevel(level_str)
    try:
        SetMemberPermissionUseCase(access, repo).execute(
            leader_id, member_id, level
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    members = GetTeamUseCase(access, repo).execute(leader_id)
    for m in members:
        if m.employee_odoo_id == member_id:
            return _member_to_view(m)
    raise HTTPException(
        status_code=404, detail="El miembro ya no pertenece al equipo"
    )


# ---------------------------------------------------------------------------
# Cualquier usuario: qué puede hacer con "su equipo" (para el gating del front)
# ---------------------------------------------------------------------------
@router.get("/my-access", response_model=MyTeamAccessView)
def get_my_team_access(
    access: TeamAccessService = Depends(get_team_access_service),
    current_user: dict = Depends(get_current_user),
):
    employee_id: int = current_user["user_id"]
    members = access.visible_team_members(employee_id)
    return MyTeamAccessView(
        is_leader=access.is_leader(employee_id),
        can_view_team=bool(members),
        can_validate_team=access.can_validate_team(employee_id),
        members=[
            TeamMemberBasicView(
                employee_odoo_id=m.employee_odoo_id, name=m.name, email=m.email
            )
            for m in members
        ],
    )


# ---------------------------------------------------------------------------
# Líder: opera siempre sobre su propio equipo (id tomado del token)
# ---------------------------------------------------------------------------
@router.get("/mine", response_model=TeamView)
def get_my_team(
    access: TeamAccessService = Depends(get_team_access_service),
    repo: SQLModelTeamPermissionRepository = Depends(get_permission_repository),
    current_user: dict = Depends(get_current_user),
):
    leader_id: int = current_user["user_id"]
    members = _get_team_or_error(
        access, repo, leader_id, not_found_status=403
    )
    return _team_to_view(leader_id, members)


@router.put("/mine/members/{member_employee_odoo_id}", response_model=TeamMemberView)
def set_my_member_permission(
    member_employee_odoo_id: int,
    request: SetPermissionRequest,
    access: TeamAccessService = Depends(get_team_access_service),
    repo: SQLModelTeamPermissionRepository = Depends(get_permission_repository),
    current_user: dict = Depends(get_current_user),
):
    leader_id: int = current_user["user_id"]
    return _apply_permission(
        access, repo, leader_id, member_employee_odoo_id, request.level
    )


# ---------------------------------------------------------------------------
# Admin (rol approver): opera sobre el equipo de cualquier líder
# ---------------------------------------------------------------------------
@router.get("/{leader_employee_odoo_id}", response_model=TeamView)
def get_team_as_admin(
    leader_employee_odoo_id: int,
    access: TeamAccessService = Depends(get_team_access_service),
    repo: SQLModelTeamPermissionRepository = Depends(get_permission_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    members = _get_team_or_error(
        access, repo, leader_employee_odoo_id, not_found_status=404
    )
    return _team_to_view(leader_employee_odoo_id, members)


@router.put(
    "/{leader_employee_odoo_id}/members/{member_employee_odoo_id}",
    response_model=TeamMemberView,
)
def set_member_permission_as_admin(
    leader_employee_odoo_id: int,
    member_employee_odoo_id: int,
    request: SetPermissionRequest,
    access: TeamAccessService = Depends(get_team_access_service),
    repo: SQLModelTeamPermissionRepository = Depends(get_permission_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    return _apply_permission(
        access,
        repo,
        leader_employee_odoo_id,
        member_employee_odoo_id,
        request.level,
    )
