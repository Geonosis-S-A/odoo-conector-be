"""Excepciones específicas del dominio de timesheet."""


class TimesheetDomainError(Exception):
    """Excepción base para errores del dominio de timesheet."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InvalidHoursError(TimesheetDomainError):
    """Error cuando las horas son inválidas (negativas)."""

    def __init__(self, hours: float):
        message = f"Las horas no pueden ser negativas. Valor recibido: {hours}"
        super().__init__(message)


class TimesheetNotFoundError(TimesheetDomainError):
    """Error cuando no se encuentra una línea de timesheet."""

    def __init__(self, timesheet_id: int):
        message = f"No se encontró la línea de timesheet con ID: {timesheet_id}"
        super().__init__(message)


class EmployeeNotFoundError(TimesheetDomainError):
    """Error cuando no se encuentra un empleado."""

    def __init__(self, employee_id: int):
        message = f"No se encontró el empleado con ID: {employee_id}"
        super().__init__(message)


class ProjectNotFoundError(TimesheetDomainError):
    """Error cuando no se encuentra un proyecto."""

    def __init__(self, project_id: int):
        message = f"No se encontró el proyecto con ID: {project_id}"
        super().__init__(message)


class OdooConnectionError(TimesheetDomainError):
    """Error de conexión con Odoo."""

    def __init__(self, original_error: str):
        message = f"Error de conexión con Odoo: {original_error}"
        super().__init__(message)


class TimesheetCreationError(TimesheetDomainError):
    """Error al crear una línea de timesheet."""

    def __init__(self, details: str = ""):
        message = f"Error al crear la línea de timesheet"
        if details:
            message += f": {details}"
        super().__init__(message)


class TimesheetUpdateError(TimesheetDomainError):
    """Error al actualizar una línea de timesheet."""

    def __init__(self, timesheet_id: int, details: str = ""):
        message = f"Error al actualizar la línea de timesheet con ID {timesheet_id}"
        if details:
            message += f": {details}"
        super().__init__(message)
