from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetDeleteError,
)


class DeleteTimesheetUseCase:
    def __init__(self, odoo_gateway: TimesheetLineGateway):
        self.odoo_gateway = odoo_gateway

    def execute(self, timesheet_ids: list[int]) -> bool:
        """Ejecuta el caso de uso para eliminar líneas de timesheet.

        Args:
            timesheet_ids: Lista de IDs de las líneas de timesheet a eliminar

        Returns:
            bool: True si la eliminación fue exitosa

        Raises:
            TimesheetNotFoundError: Si no se encuentran las líneas
            TimesheetDeleteError: Si hay un error al eliminar
        """
        # Verificar que las líneas existen
        existing_timesheets = self.odoo_gateway.get_by_ids(timesheet_ids)
        if not existing_timesheets or len(existing_timesheets) != len(timesheet_ids):
            raise TimesheetNotFoundError(timesheet_ids)

        # Eliminar en Odoo
        try:
            success = self.odoo_gateway.delete(timesheet_ids)
            if not success:
                raise TimesheetDeleteError(timesheet_ids, "La eliminación falló")
            return success
        except Exception as e:
            raise TimesheetDeleteError(timesheet_ids, str(e))
