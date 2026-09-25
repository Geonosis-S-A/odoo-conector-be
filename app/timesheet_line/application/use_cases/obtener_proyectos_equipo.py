from datetime import date
from typing import Optional

from app.project.domain.models import Project
from app.team.application.team_access import TeamAccessService
from app.timesheet_line.domain.repositories import TimesheetLineGateway


class GetTeamProjectsUseCase:
    """Proyectos donde el equipo validable del líder tiene horas cargadas.

    Intersección entre `validatable_employee_ids` (mismo criterio que
    `POST /timesheet/validate`) y los proyectos de sus líneas de timesheet
    en el rango de fechas dado. Pensado para el filtro de proyecto en la
    pantalla de validación de horas.
    """

    def __init__(
        self,
        team_access: TeamAccessService,
        timesheet_gateway: TimesheetLineGateway,
    ) -> None:
        self.team_access = team_access
        self.timesheet_gateway = timesheet_gateway

    def execute(
        self,
        leader_employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Project]:
        validatable_ids = self.team_access.validatable_employee_ids(
            leader_employee_id, date_from, date_to
        )
        if not validatable_ids:
            return []

        lines = self.timesheet_gateway.all(
            date_from=date_from,
            date_to=date_to,
            team=True,
            team_members_ids=sorted(validatable_ids),
        )

        projects_by_id: dict[int, Project] = {}
        for line in lines:
            projects_by_id[line.project.id] = line.project

        return list(projects_by_id.values())
