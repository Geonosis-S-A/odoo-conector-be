from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetValidateError,
)


class ValidateTimesheetUseCase:
    def __init__(self, odoo_gateway: TimesheetLineGateway):
        self.odoo_gateway = odoo_gateway

    def execute(self, timesheet_ids: list[int]) -> bool:
        """Ejecuta el caso de uso para validar líneas de timesheet.

        Args:
            timesheet_ids: Lista de IDs de las líneas de timesheet a validar

        Returns:
            bool: True si la validación fue exitosa

        Raises:
            TimesheetNotFoundError: Si no se encuentran las líneas
            TimesheetValidateError: Si hay un error al validar
        """
        # Verificar que las líneas existen
        existing_timesheets = self.odoo_gateway.get_by_ids(timesheet_ids)
        if not existing_timesheets or len(existing_timesheets) != len(timesheet_ids):
            raise TimesheetNotFoundError(timesheet_ids)

        # Validar en Odoo
        try:
            success = self.odoo_gateway.validate(timesheet_ids)
            if not success:
                raise TimesheetValidateError(timesheet_ids, "La validación falló")
            return success
        except Exception as e:
            raise TimesheetValidateError(timesheet_ids, str(e))
