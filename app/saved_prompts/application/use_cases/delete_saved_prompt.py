from app.saved_prompts.domain.repositories import SavedPromptRepository


class DeleteSavedPromptUseCase:
    """Caso de uso para eliminar un prompt guardado."""

    def __init__(self, repository: SavedPromptRepository):
        self.repository = repository

    def execute(self, prompt_id: int, user_id: int) -> bool:
        """Elimina un prompt guardado.

        Args:
            prompt_id: ID del prompt a eliminar
            user_id: ID del usuario (para validar ownership)

        Returns:
            bool: True si se eliminó correctamente

        Raises:
            ValueError: Si el prompt no existe o no pertenece al usuario
        """
        return self.repository.delete(prompt_id, user_id)
