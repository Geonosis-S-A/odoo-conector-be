from typing import Optional

from app.team.application.team_access import TeamAccessService
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetDeleteError,
    TimesheetDeleteForbiddenError,
)


class DeleteTimesheetUseCase:
    def __init__(
        self,
        odoo_gateway: TimesheetLineGateway,
        team_access: Optional[TeamAccessService] = None,
    ):
        self.odoo_gateway = odoo_gateway
        self.team_access = team_access

    def execute(
        self,
        timesheet_ids: list[int],
        requester_employee_id: Optional[int] = None,
    ) -> bool:
        """Ejecuta el caso de uso para eliminar líneas de timesheet.

        Args:
            timesheet_ids: Lista de IDs de las líneas de timesheet a eliminar
            requester_employee_id: Empleado que pide el borrado. Si se informa
                junto con ``team_access``, cada línea debe ser suya (y no estar
                validada) o poder ser validada por él (mismo criterio que
                validar: gerente del proyecto de la línea).

        Returns:
            bool: True si la eliminación fue exitosa

        Raises:
            TimesheetNotFoundError: Si no se encuentran las líneas
            TimesheetDeleteForbiddenError: Si alguna línea está fuera de su alcance
            TimesheetDeleteError: Si hay un error al eliminar
        """
        # Verificar que las líneas existen
        existing_timesheets = self.odoo_gateway.get_by_ids(timesheet_ids)
        if not existing_timesheets or len(existing_timesheets) != len(timesheet_ids):
            raise TimesheetNotFoundError(timesheet_ids)

        if requester_employee_id is not None and self.team_access is not None:
            authority = self.team_access.lines_authority(
                requester_employee_id,
                [(t.employee_id, t.project.id) for t in existing_timesheets],
            )
            forbidden = [
                t.id
                for t in existing_timesheets
                if not (
                    (t.employee_id == requester_employee_id and not t.validated)
                    or authority.get((t.employee_id, t.project.id), False)
                )
            ]
            if forbidden:
                raise TimesheetDeleteForbiddenError(forbidden)

        # Eliminar en Odoo
        try:
            success = self.odoo_gateway.delete(timesheet_ids)
            if not success:
                raise TimesheetDeleteError(timesheet_ids, "La eliminación falló")
            return success
        except Exception as e:
            raise TimesheetDeleteError(timesheet_ids, str(e))
