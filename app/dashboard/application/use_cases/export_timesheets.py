"""Caso de uso para exportar timesheets como excel."""

from datetime import date
from app.auth.application.use_cases.exceptions.exceptions import UserNotFound
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway
import pandas as pd


class ExportTimesheetsByTeamUseCase:
    """Caso de uso para exportar timesheets como excel por equipo."""

    def __init__(
        self,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
        manager_employee_id: int,
    ):
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway
        self.manager_employee_id = manager_employee_id

    def execute(self, date_from: date, date_to: date):
        manager_user_id = self.employee_gateway.get_user_id_by_employee_id(
            self.manager_employee_id
        )
        if not manager_user_id:
            raise UserNotFound("Manager not found")
        users = self.timesheet_line_gateway.get_team_users(
            manager_user_id, self.manager_employee_id
        )
        team_employee_ids = [user["id"] for user in users]

        # Obtengo los timesheets de los ids que paso y que pertenecen al equipo del manager
        timesheet_lines = (
            self.timesheet_line_gateway.all_by_employees_with_requester_user_id(
                team_employee_ids, date_from, date_to, manager_user_id
            )
        )

        timesheet_lines_df = pd.DataFrame(timesheet_lines)
        return timesheet_lines_df
