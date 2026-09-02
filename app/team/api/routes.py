from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles, user_has_role
from app.team.api.schemas import (
    AddMemberRequest,
    CreateTeamRequest,
    TeamMemberResponse,
    TeamResponse,
    UpdateMemberRequest,
    UpdateTeamRequest,
)
from app.team.application.use_cases.create_team import CreateTeamUseCase
from app.team.application.use_cases.delete_team import DeleteTeamUseCase
from app.team.application.use_cases.get_teams import GetTeamsUseCase
from app.team.application.use_cases.update_team import UpdateTeamUseCase
from app.team.domain.models import Team, TeamMember
from app.team.infra.db.repositories import SQLModelTeamRepository

router = APIRouter(prefix="/teams", tags=["teams"])


def get_team_repository(db: Session = Depends(get_db)) -> SQLModelTeamRepository:
    return SQLModelTeamRepository(db)


def _team_to_response(team: Team) -> TeamResponse:
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        created_at=team.created_at,
        members=[_member_to_response(m) for m in team.members],
    )


def _member_to_response(member: TeamMember) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        employee_odoo_id=member.employee_odoo_id,
        role=member.role,
        can_validate=member.can_validate,
        created_at=member.created_at,
    )


def _require_admin(current_user: dict) -> None:
    if not user_has_role(current_user.get("roles"), Roles.approver):
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")


@router.post("/", response_model=TeamResponse, status_code=201)
def create_team(
    request: CreateTeamRequest,
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        use_case = CreateTeamUseCase(repo)
        team = use_case.execute(name=request.name, description=request.description)
        return _team_to_response(team)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[TeamResponse])
def list_teams(
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    use_case = GetTeamsUseCase(repo)
    return [_team_to_response(t) for t in use_case.get_all()]


@router.get("/mine", response_model=List[TeamResponse])
def get_my_teams(
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    employee_odoo_id: int = current_user["user_id"]
    use_case = GetTeamsUseCase(repo)
    return [_team_to_response(t) for t in use_case.get_mine(employee_odoo_id)]


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    use_case = GetTeamsUseCase(repo)
    team = use_case.get_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"Equipo {team_id} no encontrado")
    return _team_to_response(team)


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    request: UpdateTeamRequest,
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        use_case = UpdateTeamUseCase(repo)
        team = use_case.update_info(
            team_id=team_id, name=request.name, description=request.description
        )
        return _team_to_response(team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{team_id}", response_model=dict)
def delete_team(
    team_id: int,
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        use_case = DeleteTeamUseCase(repo)
        use_case.execute(team_id)
        return {"message": "Equipo eliminado correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=201)
def add_member(
    team_id: int,
    request: AddMemberRequest,
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        use_case = UpdateTeamUseCase(repo)
        member = use_case.add_member(
            team_id=team_id,
            employee_odoo_id=request.employee_odoo_id,
            role=request.role,
            can_validate=request.can_validate,
        )
        return _member_to_response(member)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{team_id}/members/{employee_odoo_id}", response_model=TeamMemberResponse)
def update_member(
    team_id: int,
    employee_odoo_id: int,
    request: UpdateMemberRequest,
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        use_case = UpdateTeamUseCase(repo)
        member = use_case.update_member(
            team_id=team_id,
            employee_odoo_id=employee_odoo_id,
            role=request.role,
            can_validate=request.can_validate,
        )
        return _member_to_response(member)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{team_id}/members/{employee_odoo_id}", response_model=dict)
def remove_member(
    team_id: int,
    employee_odoo_id: int,
    repo: SQLModelTeamRepository = Depends(get_team_repository),
    current_user: dict = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        use_case = UpdateTeamUseCase(repo)
        removed = use_case.remove_member(
            team_id=team_id, employee_odoo_id=employee_odoo_id
        )
        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"Empleado {employee_odoo_id} no es miembro del equipo {team_id}",
            )
        return {"message": "Miembro eliminado correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
