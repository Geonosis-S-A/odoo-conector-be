from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetDeleteError,
)


class DeleteTimesheetUseCase:
    def __init__(self, odoo_gateway: TimesheetLineGateway):
        self.odoo_gateway = odoo_gateway

    def execute(self, timesheet_id: int) -> bool:
        """Ejecuta el caso de uso para eliminar una línea de timesheet.

        Args:
            timesheet_id: ID de la línea de timesheet a eliminar

        Returns:
            bool: True si la eliminación fue exitosa

        Raises:
            TimesheetNotFoundError: Si no se encuentra la línea
            TimesheetDeleteError: Si hay un error al eliminar
        """
        # Verificar que la línea existe
        existing_timesheet = self.odoo_gateway.get_by_id(timesheet_id)
        if existing_timesheet is None:
            raise TimesheetNotFoundError(timesheet_id)

        # Eliminar en Odoo
        try:
            success = self.odoo_gateway.delete(timesheet_id)
            if not success:
                raise TimesheetDeleteError(timesheet_id, "La eliminación falló")
            return success
        except Exception as e:
            raise TimesheetDeleteError(timesheet_id, str(e))
