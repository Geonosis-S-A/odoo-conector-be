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

        # Se muestran todos los permisos, también los vencidos o futuros: el
        # líder necesita verlos para renovarlos o quitarlos.
        permissions = {
            p.member_employee_odoo_id: p
            for p in self.permission_repo.list_by_leader(leader_employee_id)
        }
        members: List[TeamMemberInfo] = []
        for u in team:
            perm = permissions.get(u["id"])
            members.append(
                TeamMemberInfo(
                    employee_odoo_id=u["id"],
                    name=u.get("name"),
                    email=u.get("work_email") or None,
                    level=perm.level if perm else None,
                    valid_from=perm.valid_from if perm else None,
                    valid_until=perm.valid_until if perm else None,
                )
            )
        return members
