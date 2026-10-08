"""Excepciones específicas del dominio de timesheet."""

from datetime import date
from typing import Optional


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


class OdooValidationError(TimesheetDomainError):
    """Error de validación específico de Odoo que contiene el mensaje original."""

    def __init__(self, odoo_error_message: str, fault_code: str = ""):
        """
        Args:
            odoo_error_message: Mensaje de error original de Odoo
            fault_code: Código de error de Odoo (opcional)
        """
        self.odoo_error_message = odoo_error_message
        self.fault_code = fault_code
        # Usar el mensaje original de Odoo como mensaje de la excepción
        super().__init__(odoo_error_message)


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


class EmployeeNotHasUserError(TimesheetDomainError):
    """Error cuando un empleado no tiene usuario asignado en odoo."""

    def __init__(self, employee_id: int):
        message = f"El empleado con ID {employee_id} no tiene usuario asignado en odoo"
        super().__init__(message)


class ProjectNotManagedError(TimesheetDomainError):
    """Error cuando se filtra por equipo dentro de un proyecto que el
    solicitante no gerencia en Odoo."""

    def __init__(self, project_id: int):
        message = f"No gerenciás el proyecto {project_id}"
        super().__init__(message)


class EmployeeNotAssignedToProjectError(TimesheetDomainError):
    """Error cuando un empleado carga horas a un proyecto sin asignación vigente."""

    def __init__(
        self,
        employee_id: int,
        project_id: int,
        project_name: Optional[str] = None,
        assigned_from: Optional[date] = None,
        requested_date: Optional[date] = None,
    ):
        self.employee_id = employee_id
        self.project_id = project_id
        project = f"«{project_name}»" if project_name else f"{project_id}"
        if assigned_from and requested_date and requested_date < assigned_from:
            message = (
                f"No podés cargar horas al proyecto {project} con fecha "
                f"{requested_date:%d/%m/%Y}: tu asignación comienza el "
                f"{assigned_from:%d/%m/%Y}."
            )
        else:
            message = (
                f"No tenés una asignación vigente al proyecto {project}. "
                f"Consultá con el gerente del proyecto."
            )
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

    def __init__(self, timesheet_ids: list[int], details: str = ""):
        message = f"Error al eliminar la línea de timesheet con ID {timesheet_ids}"
        if details:
            message += f": {details}"
        super().__init__(message)


class TimesheetDeleteForbiddenError(TimesheetDomainError):
    """El solicitante no puede borrar alguna de las líneas pedidas."""

    def __init__(self, timesheet_ids: list[int]):
        message = (
            "No tienes permiso para eliminar las líneas de timesheet con IDs "
            f"{timesheet_ids}"
        )
        super().__init__(message)


class TimesheetValidateError(TimesheetDomainError):
    """Error al validar una línea de timesheet."""

    def __init__(self, timesheet_ids: list[int], details: str = ""):
        message = f"Error al validar las líneas de timesheet con IDs {timesheet_ids}"
        if details:
            message += f": {details}"
        super().__init__(message)


class ApproverNotFoundError(TimesheetDomainError):
    """Error cuando no se encuentra el approver."""

    def __init__(self, approver_email: str):
        message = f"El empleado que intenta enviar el correo de revisión no existe: {approver_email}"
        super().__init__(message)


class TimesheetReviewError(TimesheetDomainError):
    """Error al enviar correos de revisión de timesheet."""

    def __init__(self, details: str = ""):
        message = "Error al enviar correos de revisión"
        if details:
            message += f": {details}"
        super().__init__(message)