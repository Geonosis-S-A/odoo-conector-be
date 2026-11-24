from app.timesheet_line.api.schemas import EditTimesheetRequest
from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.domain.limits import MAX_HOURS_PER_DAY
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    DailyHoursLimitExceededError,
    InvalidHoursError,
    TimesheetNotFoundError,
    TimesheetEditError,
)


class EditTimesheetUseCase:
    def __init__(self, odoo_gateway: TimesheetLineGateway):
        self.odoo_gateway = odoo_gateway

    def execute(self, req: EditTimesheetRequest) -> bool:
        """Ejecuta el caso de uso para editar una línea de hoja de tiempo.

        Args:
            req: Datos de la línea de hoja de tiempo a editar

        Returns:
            bool: True si la edición fue exitosa

        Raises:
            InvalidHoursError: Si las horas son negativas
            TimesheetNotFoundError: Si no se encuentra la línea
            TimesheetEditError: Si hay un error al actualizar
        """
        # Validación de horas negativas
        if req.hours < 0:
            raise InvalidHoursError(req.hours)

        # Verificar que la línea existe
        existing_timesheet = self.odoo_gateway.get_by_id(req.id)
        if existing_timesheet is None:
            raise TimesheetNotFoundError([req.id])

        # Máximo de horas por día: lo que ya tiene ese día (sin contar esta línea)
        # más las horas editadas.
        others = sum(
            line.hours
            for line in self.odoo_gateway.all(
                employee_id=req.employee_id, date_from=req.date, date_to=req.date
            )
            if line.id != req.id
        )
        if others + req.hours > MAX_HOURS_PER_DAY:
            raise DailyHoursLimitExceededError(
                req.date, others, req.hours, MAX_HOURS_PER_DAY
            )

        # Crear el objeto de dominio
        timesheet_line = TimesheetLine(
            id=req.id,
            name=req.name,
            employee_id=req.employee_id,
            project_id=req.project_id,
            hours=req.hours,
            date=req.date,
            task_id=req.task_id,
        )

        # Actualizar en Odoo
        try:
            success = self.odoo_gateway.update(timesheet_line)
            if success is None or not success:
                raise TimesheetEditError(req.id, "La actualización falló")
            return success
        except Exception as e:
            raise TimesheetEditError(req.id, str(e))
