from datetime import date
from typing import Optional

from app.team.application.team_access import TeamAccessService
from app.team.domain.models import PermissionLevel, TeamMemberPermission
from app.team.domain.repositories import TeamPermissionRepository


class SetMemberPermissionUseCase:
    """Fija (o elimina) la delegación de aprobación de un gerente de proyectos en
    uno de los PM de sus proyectos."""

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
        if level is None:
            # Quitar una delegación se permite siempre, también si la persona ya
            # dejó de ser PM de sus proyectos: si no, quedaría sin poder borrarse.
            self.permission_repo.delete(leader_employee_id, member_employee_id)
            return None

        if not self.team_access.is_project_head(leader_employee_id):
            raise ValueError(
                "Solo los gerentes de proyectos pueden delegar la aprobación"
            )
        candidate_ids = {
            u["id"]
            for u in self.team_access.get_coverage_candidates(leader_employee_id)
        }
        if member_employee_id not in candidate_ids:
            raise ValueError(
                "La persona indicada no es PM de ninguno de los proyectos que "
                "gerencia este líder"
            )

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
