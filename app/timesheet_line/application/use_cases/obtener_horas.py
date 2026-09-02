from dataclasses import replace
from typing import List, Optional
from datetime import date

from app.timesheet_line.api.schemas import TimesheetLineNotificationResponse
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import (
    TimesheetLineGateway,
    TimesheetLineNotificationRepository,
)
from app.task.domain.gateway import TaskGateway
from app.task.domain.task_hierarchy import (
    collect_tasks_info_with_ancestors,
    full_task_display_name,
)
from app.users.domain.repositories import EmployeeGateway
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetListError,
    InvalidDateRangeError,
    InvalidEmployeeIdError,
    EmployeeNotExistsError,
    EmployeeNotHasUserError,
)
from app.team.domain.repositories import TeamRepository


class ListTimesheetLinesUseCase:
    def __init__(
        self,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
        notification_repository: TimesheetLineNotificationRepository,
        task_gateway: TaskGateway | None = None,
        team_repository: Optional[TeamRepository] = None,
    ) -> None:
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway
        self.notification_repository: TimesheetLineNotificationRepository = (
            notification_repository
        )
        self.task_gateway = task_gateway
        self.team_repository = team_repository

    def execute(
        self,
        employee_id: int | None,
        date_from: date | None,
        date_to: date | None,
        project_id: int | None,
        validated: bool | None,
        team: bool | None,
        id: int | None,
    ) -> List[DetailedTimesheetLine]:
        # Validación de employee_id
        if employee_id is not None and employee_id <= 0:
            raise InvalidEmployeeIdError(employee_id)

        # Verificar si el empleado existe
        if employee_id is not None and not self.employee_gateway.exists_by_id(
            employee_id
        ):
            raise EmployeeNotExistsError(employee_id)

        user_id = None
        ids = None
        if id is not None and team and employee_id is None:
            # 1. Buscar equipo en BD local (soporta sub_leaders sin usuario Odoo)
            if self.team_repository:
                local_ids = self.team_repository.get_team_member_ids_by_any_leader(id)
                if local_ids:
                    ids = local_ids
            # 2. Fallback: jerarquía de Odoo (comportamiento legacy)
            if ids is None:
                user_id = self.employee_gateway.get_user_id_by_employee_id(id)
                if user_id is None:
                    raise EmployeeNotHasUserError(id)
                users = self.timesheet_line_gateway.get_team_users(user_id, id)
                ids = [user["id"] for user in users]


        # Validación de rango de fechas
        if date_from is not None and date_to is not None and date_from > date_to:
            raise InvalidDateRangeError(date_from.isoformat(), date_to.isoformat())

        

        timesheets = self.timesheet_line_gateway.all(
            employee_id, date_from, date_to, project_id, validated, team, user_id, ids,
        )

        if self.task_gateway and timesheets:
            task_ids = [t.task.id for t in timesheets if t.task is not None]
            if task_ids:
                tasks_info = collect_tasks_info_with_ancestors(
                    self.task_gateway, task_ids
                )
                for line in timesheets:
                    if line.task is None:
                        continue
                    full_name = full_task_display_name(line.task.id, tasks_info)
                    if full_name:
                        line.task = replace(line.task, name=full_name)

        employees = self.employee_gateway.all()
        employees_dict = {employee.id: employee for employee in employees}

        # Una sola query batch para todas las notificaciones (reemplaza el loop N+1)
        notifications = self.notification_repository.get_by_timesheet_ids(
            [t.id for t in timesheets]
        )
        notifications_map = {n.timesheet_line_id: n for n in notifications}

        for timesheet in timesheets:
            notification = notifications_map.get(timesheet.id)
            if notification is not None:
                timesheet.notification = TimesheetLineNotificationResponse(
                    id=notification.id,
                    sender_name=employees_dict[notification.approver_id].full_name,
                    sended_at=notification.created_at,
                )
        return timesheets
