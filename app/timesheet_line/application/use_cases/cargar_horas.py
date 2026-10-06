# Es un ejemplo, podría tener otro nombre etc

from typing import List, Optional
from app.project.domain.gateway import ProjectAssignmentGateway
from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    EmployeeNotAssignedToProjectError,
    InvalidHoursError,
    TimesheetCreationError,
    TimesheetNotFoundError,
)
from app.users.domain.repositories import EmployeeGateway


class CargarHorasUseCase:
    def __init__(
        self,
        timesheet_line_gateway: TimesheetLineGateway,
        project_assignment_gateway: ProjectAssignmentGateway,
        employee_gateway: Optional[EmployeeGateway] = None,
    ):
        self.timesheet_line_gateway = timesheet_line_gateway
        self.project_assignment_gateway = project_assignment_gateway
        self.employee_gateway = employee_gateway

    def _can_load_hours(self, req: CargarHorasRequest) -> bool:
        """Asignación vigente al proyecto en la fecha de la línea, o ser el
        gerente del proyecto (mismo criterio que ``GET /projects/``)."""
        if self.project_assignment_gateway.is_employee_assigned(
            req.employee_id, req.project_id, req.date
        ):
            return True
        if self.employee_gateway is None:
            return False
        user_id = self.employee_gateway.get_user_id_by_employee_id(req.employee_id)
        if user_id is None:
            return False
        managers = self.project_assignment_gateway.get_project_manager_user_ids(
            [req.project_id]
        )
        return managers.get(req.project_id) == user_id

    def execute(
        self, requests: list[CargarHorasRequest]
    ) -> list[DetailedTimesheetLine]:
        """
        Ejecuta la creación de líneas de timesheet.

        Sólo se puede cargar horas a proyectos a los que el empleado está
        asignado (``project.assignment`` vigente en la fecha de la línea) o
        que gerencia. Se valida todo el lote antes de crear nada.

        Args:
            requests: Lista de peticiones para crear líneas de timesheet

        Returns:
            list[DetailedTimesheetLine]: Lista de líneas de timesheet creadas

        Raises:
            InvalidHoursError: Cuando las horas son negativas
            EmployeeNotAssignedToProjectError: Sin asignación ni gerencia del proyecto
            TimesheetCreationError: Para errores de creación
            TimesheetNotFoundError: Cuando no se pueden obtener las líneas creadas
        """
        timesheet_lines = []
        for req in requests:
            if req.hours < 0:
                raise InvalidHoursError(req.hours)

            if not self._can_load_hours(req):
                raise EmployeeNotAssignedToProjectError(
                    req.employee_id, req.project_id
                )

            timesheet_line = TimesheetLine.from_request(
                id=None,
                name=req.name,
                employee_id=req.employee_id,
                project_id=req.project_id,
                hours=req.hours,
                date=req.date,
                task_id=req.task_id,
            )
            timesheet_lines.append(timesheet_line)

        # Crear todas las líneas en batch
        line_ids = self.timesheet_line_gateway.create(timesheet_lines)
        if not line_ids:
            raise TimesheetCreationError()

        # Obtener todas las líneas creadas
        new_timesheet_lines = self.timesheet_line_gateway.get_by_ids(line_ids)
        if not new_timesheet_lines:
            raise TimesheetCreationError(
                "No se pudieron obtener las líneas de timesheet creadas"
            )

        return new_timesheet_lines
