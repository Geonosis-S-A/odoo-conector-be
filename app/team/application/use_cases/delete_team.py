from app.team.domain.repositories import TeamRepository


class DeleteTeamUseCase:
    def __init__(self, team_repository: TeamRepository) -> None:
        self.repo = team_repository

    def execute(self, team_id: int) -> bool:
        team = self.repo.get_by_id(team_id)
        if team is None:
            raise ValueError(f"Equipo {team_id} no encontrado")
        return self.repo.delete(team_id)
