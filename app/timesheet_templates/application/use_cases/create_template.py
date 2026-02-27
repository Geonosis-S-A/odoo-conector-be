from typing import Optional
from app.timesheet_templates.domain.models import TimesheetTemplate
from app.timesheet_templates.domain.repositories import TimesheetTemplateRepository


class CreateTimesheetTemplateUseCase:
    """Caso de uso para crear un template de carga de timesheet."""

    def __init__(self, repository: TimesheetTemplateRepository):
        self.repository = repository

    def execute(
        self,
        user_id: int,
        name: str,
        project_id: int,
        task_id: Optional[int] = None,
    ) -> TimesheetTemplate:
        """Crea un nuevo template.

        Args:
            user_id: ID del usuario propietario
            name: Nombre descriptivo del template
            project_id: ID del proyecto en Odoo
            task_id: ID de la tarea en Odoo (opcional)

        Returns:
            TimesheetTemplate: El template creado con su ID asignado

        Raises:
            ValueError: Si el nombre está vacío o el project_id es inválido
        """
        if not name or not name.strip():
            raise ValueError("El nombre del template no puede estar vacío")

        if project_id <= 0:
            raise ValueError("El template debe tener un proyecto válido")

        template = TimesheetTemplate(
            user_id=user_id,
            name=name.strip(),
            project_id=project_id,
            task_id=task_id,
        )

        return self.repository.create(template)
