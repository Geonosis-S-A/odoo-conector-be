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

    def __init__(self, timesheet_ids: list[int]):
        message = f"No se encontraron las líneas de timesheet con IDs: {timesheet_ids}"
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
        message = "Error al crear la línea de timesheet"
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


class TimesheetListError(TimesheetDomainError):
    """Error al listar las líneas de timesheet."""

    def __init__(self, details: str = ""):
        message = "Error al obtener las líneas de timesheet"
        if details:
            message += f": {details}"
        super().__init__(message)


class InvalidDateRangeError(TimesheetDomainError):
    """Error cuando el rango de fechas es inválido."""

    def __init__(self, date_from: str, date_to: str):
        message = f"Rango de fechas inválido: fecha_desde ({date_from}) debe ser anterior a fecha_hasta ({date_to})"
        super().__init__(message)


class InvalidEmployeeIdError(TimesheetDomainError):
    """Error cuando el ID del empleado es inválido."""

    def __init__(self, employee_id: int):
        message = f"ID de empleado inválido: {employee_id}"
        super().__init__(message)


class EmployeeNotExistsError(TimesheetDomainError):
    """Error cuando el empleado no existe en el sistema."""

    def __init__(self, employee_id: int):
        message = f"El empleado con ID {employee_id} no existe en el sistema"
        super().__init__(message)


class TimesheetIdMismatchError(TimesheetDomainError):
    """Error cuando el ID en la URL no coincide con el ID en el body."""

    def __init__(self, url_id: int, body_id: int):
        message = (
            f"El ID en la URL ({url_id}) no coincide con el ID en el body ({body_id})"
        )
        super().__init__(message)


class TimesheetEditError(TimesheetDomainError):
    """Error al editar una línea de timesheet."""

    def __init__(self, timesheet_id: int, details: str = ""):
        message = f"Error al editar la línea de timesheet con ID {timesheet_id}"
        if details:
            message += f": {details}"
        super().__init__(message)


class TimesheetDeleteError(TimesheetDomainError):
    """Error al eliminar una línea de timesheet."""

    def __init__(self, timesheet_id: int, details: str = ""):
        message = f"Error al eliminar la línea de timesheet con ID {timesheet_id}"
        if details:
            message += f": {details}"
        super().__init__(message)
