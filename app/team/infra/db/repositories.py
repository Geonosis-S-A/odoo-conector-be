from typing import List, Optional

from sqlmodel import Session, select

from app.team.domain.models import Team, TeamMember, TeamRole, ROLES_WITH_TEAM_VIEW
from app.team.domain.repositories import TeamRepository
from app.team.infra.db.models import TeamMemberModel, TeamModel


def _member_model_to_domain(m: TeamMemberModel) -> TeamMember:
    return TeamMember(
        id=m.id,
        team_id=m.team_id,
        employee_odoo_id=m.employee_odoo_id,
        role=TeamRole(m.role),
        can_validate=m.can_validate,
        created_at=m.created_at,
    )


def _team_model_to_domain(t: TeamModel) -> Team:
    return Team(
        id=t.id,
        name=t.name,
        description=t.description,
        created_at=t.created_at,
        members=[_member_model_to_domain(m) for m in (t.members or [])],
    )


class SQLModelTeamRepository(TeamRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, team: Team) -> Team:
        model = TeamModel(name=team.name, description=team.description)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _team_model_to_domain(model)

    def get_by_id(self, team_id: int) -> Optional[Team]:
        model = self.db.get(TeamModel, team_id)
        if model is None:
            return None
        self.db.refresh(model)
        return _team_model_to_domain(model)

    def get_all(self) -> List[Team]:
        models = self.db.exec(select(TeamModel)).all()
        return [_team_model_to_domain(t) for t in models]

    def get_by_employee_odoo_id(self, employee_odoo_id: int) -> List[Team]:
        member_rows = self.db.exec(
            select(TeamMemberModel).where(
                TeamMemberModel.employee_odoo_id == employee_odoo_id
            )
        ).all()
        teams = []
        seen = set()
        for member in member_rows:
            if member.team_id not in seen:
                seen.add(member.team_id)
                team_model = self.db.get(TeamModel, member.team_id)
                if team_model:
                    teams.append(_team_model_to_domain(team_model))
        return teams

    def update(self, team: Team) -> Team:
        model = self.db.get(TeamModel, team.id)
        if model is None:
            raise ValueError(f"Equipo {team.id} no encontrado")
        model.name = team.name
        model.description = team.description
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _team_model_to_domain(model)

    def delete(self, team_id: int) -> bool:
        model = self.db.get(TeamModel, team_id)
        if model is None:
            return False
        # Eliminar miembros primero
        members = self.db.exec(
            select(TeamMemberModel).where(TeamMemberModel.team_id == team_id)
        ).all()
        for m in members:
            self.db.delete(m)
        self.db.delete(model)
        self.db.commit()
        return True

    def add_member(self, member: TeamMember) -> TeamMember:
        model = TeamMemberModel(
            team_id=member.team_id,
            employee_odoo_id=member.employee_odoo_id,
            role=member.role.value,
            can_validate=member.can_validate,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _member_model_to_domain(model)

    def update_member(self, member: TeamMember) -> TeamMember:
        model = self.db.get(TeamMemberModel, member.id)
        if model is None:
            raise ValueError(f"Miembro {member.id} no encontrado")
        model.role = member.role.value
        model.can_validate = member.can_validate
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _member_model_to_domain(model)

    def remove_member(self, team_id: int, employee_odoo_id: int) -> bool:
        model = self.db.exec(
            select(TeamMemberModel).where(
                TeamMemberModel.team_id == team_id,
                TeamMemberModel.employee_odoo_id == employee_odoo_id,
            )
        ).first()
        if model is None:
            return False
        self.db.delete(model)
        self.db.commit()
        return True

    def get_member(self, team_id: int, employee_odoo_id: int) -> Optional[TeamMember]:
        model = self.db.exec(
            select(TeamMemberModel).where(
                TeamMemberModel.team_id == team_id,
                TeamMemberModel.employee_odoo_id == employee_odoo_id,
            )
        ).first()
        if model is None:
            return None
        return _member_model_to_domain(model)

    def get_member_employee_ids(self, team_id: int) -> List[int]:
        rows = self.db.exec(
            select(TeamMemberModel.employee_odoo_id).where(
                TeamMemberModel.team_id == team_id
            )
        ).all()
        return list(rows)

    def get_member_record(self, employee_odoo_id: int) -> Optional[TeamMember]:
        model = self.db.exec(
            select(TeamMemberModel).where(
                TeamMemberModel.employee_odoo_id == employee_odoo_id
            )
        ).first()
        if model is None:
            return None
        return _member_model_to_domain(model)

    def get_team_member_ids_by_any_leader(self, employee_odoo_id: int) -> List[int]:
        view_roles = [r.value for r in ROLES_WITH_TEAM_VIEW]
        my_member = self.db.exec(
            select(TeamMemberModel).where(
                TeamMemberModel.employee_odoo_id == employee_odoo_id,
                TeamMemberModel.role.in_(view_roles),  # type: ignore[attr-defined]
            )
        ).first()
        if my_member is None:
            return []
        return self.get_member_employee_ids(my_member.team_id)
