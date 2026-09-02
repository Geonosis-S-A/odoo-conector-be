from typing import List, Optional

from app.team.domain.models import Team
from app.team.domain.repositories import TeamRepository


class GetTeamsUseCase:
    def __init__(self, team_repository: TeamRepository) -> None:
        self.repo = team_repository

    def get_all(self) -> List[Team]:
        return self.repo.get_all()

    def get_by_id(self, team_id: int) -> Optional[Team]:
        return self.repo.get_by_id(team_id)

    def get_mine(self, employee_odoo_id: int) -> List[Team]:
        return self.repo.get_by_employee_odoo_id(employee_odoo_id)
