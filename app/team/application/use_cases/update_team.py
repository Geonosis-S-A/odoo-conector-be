from typing import Optional

from app.team.domain.models import Team, TeamMember, TeamRole
from app.team.domain.repositories import TeamRepository


class UpdateTeamUseCase:
    def __init__(self, team_repository: TeamRepository) -> None:
        self.repo = team_repository

    def update_info(self, team_id: int, name: str, description: Optional[str]) -> Team:
        team = self.repo.get_by_id(team_id)
        if team is None:
            raise ValueError(f"Equipo {team_id} no encontrado")
        team.name = name
        team.description = description
        return self.repo.update(team)

    def add_member(
        self,
        team_id: int,
        employee_odoo_id: int,
        role: TeamRole,
        can_validate: bool = False,
    ) -> TeamMember:
        team = self.repo.get_by_id(team_id)
        if team is None:
            raise ValueError(f"Equipo {team_id} no encontrado")
        existing = self.repo.get_member(team_id, employee_odoo_id)
        if existing is not None:
            raise ValueError(
                f"El empleado {employee_odoo_id} ya es miembro del equipo {team_id}"
            )
        member = TeamMember.create(
            team_id=team_id,
            employee_odoo_id=employee_odoo_id,
            role=role,
            can_validate=can_validate,
        )
        return self.repo.add_member(member)

    def update_member(
        self,
        team_id: int,
        employee_odoo_id: int,
        role: TeamRole,
        can_validate: bool,
    ) -> TeamMember:
        member = self.repo.get_member(team_id, employee_odoo_id)
        if member is None:
            raise ValueError(
                f"El empleado {employee_odoo_id} no es miembro del equipo {team_id}"
            )
        member.role = role
        member.can_validate = TeamMember._resolve_can_validate(role, can_validate)
        return self.repo.update_member(member)

    def remove_member(self, team_id: int, employee_odoo_id: int) -> bool:
        team = self.repo.get_by_id(team_id)
        if team is None:
            raise ValueError(f"Equipo {team_id} no encontrado")
        return self.repo.remove_member(team_id, employee_odoo_id)
