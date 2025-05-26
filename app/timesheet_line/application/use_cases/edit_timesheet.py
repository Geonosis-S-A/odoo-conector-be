from app.timesheet_line.api.schemas import EditTimesheetRequest
from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway


class EditTimesheetUseCase:
    def __init__(self, odoo_gateway: TimesheetLineGateway):
        self.odoo_gateway = odoo_gateway

    def execute(self, req: EditTimesheetRequest) -> bool:
        """Ejecuta el caso de uso para editar una línea de hoja de tiempo.

        Args:
            req: Datos de la línea de hoja de tiempo a editar

        Returns:
            bool: True si la edición fue exitosa, False en caso contrario

        Raises:
            ValueError: Si las horas son negativas o si no se encuentra la línea
        """
        # Validación de horas negativas
        if req.hours < 0:
            raise ValueError("Las horas no pueden ser negativas")

        # Verificar que la línea existe
        try:
            self.odoo_gateway.get_by_id(req.id)
        except ValueError:
            raise ValueError("No se encontró la línea de timesheet")

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
        return self.odoo_gateway.update(timesheet_line)
