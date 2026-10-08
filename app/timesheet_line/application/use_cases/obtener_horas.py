from dataclasses import replace
from typing import Any, Dict, List, Optional
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
    ProjectNotManagedError,
)
from app.team.application.team_access import TeamAccessService


class ListTimesheetLinesUseCase:
    def __init__(
        self,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
        notification_repository: TimesheetLineNotificationRepository,
        task_gateway: TaskGateway | None = None,
        team_access: Optional[TeamAccessService] = None,
    ) -> None:
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway
        self.notification_repository: TimesheetLineNotificationRepository = (
            notification_repository
        )
        self.task_gateway = task_gateway
        self.team_access = team_access

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
        project_wide = False
        if id is not None and team and employee_id is None:
            if self.team_access is None:
                raise EmployeeNotHasUserError(id)
            if project_id is not None:
                # Validación "por proyecto": sólo quienes el líder asignó a
                # ESE proyecto puntual (project.assignment), no jerarquía.
                if not self.team_access.manages_project(id, project_id):
                    raise ProjectNotManagedError(project_id)
                # El alcance lo da el proyecto: todas las líneas de ESE
                # proyecto, también las de quien cargó sin (o antes de tener)
                # asignación. No se resuelve el equipo del líder.
                project_wide = True
            else:
                # Vista plana de equipo = jerarquía ∪ proyectos gerenciados
                # + permisos locales.
                ids = sorted(
                    self.team_access.visible_employee_ids(id, date_from, date_to)
                )


        # Validación de rango de fechas
        if date_from is not None and date_to is not None and date_from > date_to:
            raise InvalidDateRangeError(date_from.isoformat(), date_to.isoformat())

        

        extra = {"project_wide": True} if project_wide else {}
        timesheets = self.timesheet_line_gateway.all(
            employee_id, date_from, date_to, project_id, validated, team, user_id, ids,
            **extra,
        )
        if project_wide:
            # Sin auto-aprobación: las horas del propio líder no van en su
            # vista de validación (antes quedaban afuera al resolver el equipo).
            timesheets = [t for t in timesheets if t.employee_id != id]

        # Marcar por línea si el usuario puede validarla/borrarla (para los
        # botones del front). Se decide por el gerente del proyecto de cada
        # línea, no por la relación con el empleado: ver a alguien (jerarquía)
        # no implica poder aprobar sus horas en proyectos de otro líder. El
        # rol approver no habilita actuar fuera de ese alcance.
        if (
            team
            and timesheets
            and self.team_access is not None
            and id is not None
        ):
            authority = self.team_access.lines_authority(
                id, [(line.employee_id, line.project.id) for line in timesheets]
            )
            approver_names = self.team_access.project_approver_names(
                [line.project.id for line in timesheets]
            )
            for line in timesheets:
                allowed = authority.get((line.employee_id, line.project.id), False)
                line.can_validate = allowed and not line.validated
                line.can_delete = allowed
                line.approver_names = approver_names.get(line.project.id, [])

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

        # Una sola query batch para todas las notificaciones (reemplaza el loop N+1)
        notifications = self.notification_repository.get_by_timesheet_ids(
            [t.id for t in timesheets]
        )
        notifications_map = {n.timesheet_line_id: n for n in notifications}

        # Sólo resolvemos los empleados de las notificaciones encontradas
        # (antes se traía la empresa entera con employee_gateway.all(),
        # paginado, aunque no hubiera ninguna notificación que mostrar).
        employees_dict: Dict[int, Any] = {}
        if notifications:
            approver_ids = {n.approver_id for n in notifications}
            employees_dict = {
                employee.id: employee
                for employee in self.employee_gateway.get_by_ids(list(approver_ids))
            }

        for timesheet in timesheets:
            notification = notifications_map.get(timesheet.id)
            if notification is not None:
                timesheet.notification = TimesheetLineNotificationResponse(
                    id=notification.id,
                    sender_name=employees_dict[notification.approver_id].full_name,
                    sended_at=notification.created_at,
                )
        return timesheets
