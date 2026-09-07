from typing import List

from app.team.application.team_access import TeamAccessService, TeamMemberInfo
from app.team.domain.repositories import TeamPermissionRepository


class GetTeamUseCase:
    """Lista el equipo Odoo de un líder con el nivel de permiso de cada miembro."""

    def __init__(
        self,
        team_access: TeamAccessService,
        permission_repo: TeamPermissionRepository,
    ) -> None:
        self.team_access = team_access
        self.permission_repo = permission_repo

    def execute(self, leader_employee_id: int) -> List[TeamMemberInfo]:
        team = self.team_access.get_led_team(leader_employee_id)
        if not team:
            return []

        levels = {
            p.member_employee_odoo_id: p.level
            for p in self.permission_repo.list_by_leader(leader_employee_id)
        }
        return [
            TeamMemberInfo(
                employee_odoo_id=u["id"],
                name=u.get("name"),
                email=u.get("work_email") or None,
                level=levels.get(u["id"]),
            )
            for u in team
        ]
