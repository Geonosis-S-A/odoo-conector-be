from datetime import date
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
        valid_from: Optional[date] = None,
        valid_until: Optional[date] = None,
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

        if (
            valid_from is not None
            and valid_until is not None
            and valid_from > valid_until
        ):
            raise ValueError("La fecha 'desde' no puede ser posterior a la fecha 'hasta'")
        if valid_until is not None and valid_until < date.today():
            raise ValueError("La fecha 'hasta' ya pasó: el permiso no tendría efecto")

        return self.permission_repo.upsert(
            TeamMemberPermission(
                id=None,
                leader_employee_odoo_id=leader_employee_id,
                member_employee_odoo_id=member_employee_id,
                level=level,
                valid_from=valid_from,
                valid_until=valid_until,
            )
        )
