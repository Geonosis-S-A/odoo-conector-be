from app.team.domain.models import Team
from app.team.domain.repositories import TeamRepository


class CreateTeamUseCase:
    def __init__(self, team_repository: TeamRepository) -> None:
        self.repo = team_repository

    def execute(self, name: str, description: str | None = None) -> Team:
        team = Team.create(name=name, description=description)
        return self.repo.create(team)
