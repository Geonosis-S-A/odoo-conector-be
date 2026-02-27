from typing import List
from app.timesheet_templates.domain.models import TimesheetTemplate
from app.timesheet_templates.domain.repositories import TimesheetTemplateRepository


class ListTimesheetTemplatesUseCase:
    """Caso de uso para listar los templates de un usuario."""

    def __init__(self, repository: TimesheetTemplateRepository):
        self.repository = repository

    def execute(self, user_id: int) -> List[TimesheetTemplate]:
        """Lista todos los templates del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            List[TimesheetTemplate]: Lista de templates del usuario, ordenados por fecha de creación
        """
        return self.repository.list_by_user(user_id)
