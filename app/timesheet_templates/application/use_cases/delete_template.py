from app.timesheet_templates.domain.repositories import TimesheetTemplateRepository


class DeleteTimesheetTemplateUseCase:
    """Caso de uso para eliminar un template de carga de timesheet."""

    def __init__(self, repository: TimesheetTemplateRepository):
        self.repository = repository

    def execute(self, template_id: int, user_id: int) -> None:
        """Elimina un template si pertenece al usuario.

        Args:
            template_id: ID del template a eliminar
            user_id: ID del usuario (para validar ownership)

        Raises:
            ValueError: Si el template no existe o no pertenece al usuario
        """
        self.repository.delete(template_id, user_id)
