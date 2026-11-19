from typing import List

from app.team.application.team_access import LedProjectTeam, TeamAccessService


class GetTeamByProjectUseCase:
    """Proyectos que gerencia un líder, con los empleados asignados a cada uno."""

    def __init__(self, team_access: TeamAccessService) -> None:
        self.team_access = team_access

    def execute(self, leader_employee_id: int) -> List[LedProjectTeam]:
        return self.team_access.get_led_team_by_project(leader_employee_id)
