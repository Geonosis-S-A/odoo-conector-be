from typing import Optional

from app.team.application.team_access import TeamAccessService
from app.team.domain.models import PermissionLevel, TeamMemberPermission
from app.team.domain.repositories import TeamPermissionRepository


class SetMemberPermissionUseCase:
    """Fija (o elimina) el permiso de un miembro dentro del equipo Odoo de un líder."""

    def __init__(
        self,
        team_access: TeamAccessService,
        permission_repo: TeamPermissionRepository,
    ) -> None:
        self.team_access = team_access
        self.permission_repo = permission_repo

    def execute(
        self,
        leader_employee_id: int,
        member_employee_id: int,
        level: Optional[PermissionLevel],
    ) -> Optional[TeamMemberPermission]:
        team_ids = self.team_access.get_led_team_member_ids(leader_employee_id)
        if not team_ids:
            raise ValueError(
                f"El empleado {leader_employee_id} no lidera un equipo en Odoo"
            )
        if member_employee_id not in team_ids:
            raise ValueError(
                "La persona indicada no pertenece al equipo de este líder en Odoo"
            )

        if level is None:
            self.permission_repo.delete(leader_employee_id, member_employee_id)
            return None

        return self.permission_repo.upsert(
            TeamMemberPermission(
                id=None,
                leader_employee_odoo_id=leader_employee_id,
                member_employee_odoo_id=member_employee_id,
                level=level,
            )
        )
