from typing import List
from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository


class ListSavedPromptsUseCase:
    """Caso de uso para listar los prompts guardados de un usuario."""

    def __init__(self, repository: SavedPromptRepository):
        self.repository = repository

    def execute(self, user_id: int) -> List[SavedPrompt]:
        """Lista todos los prompts guardados de un usuario.

        Args:
            user_id: ID del usuario (employee_id)

        Returns:
            List[SavedPrompt]: Lista de prompts guardados del usuario
        """
        return self.repository.list_by_user(user_id)
