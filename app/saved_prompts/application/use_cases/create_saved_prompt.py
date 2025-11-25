from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository


class CreateSavedPromptUseCase:
    """Caso de uso para crear un prompt guardado."""

    def __init__(self, repository: SavedPromptRepository):
        self.repository = repository

    def execute(self, user_id: int, prompt_text: str) -> SavedPrompt:
        """Crea un nuevo prompt guardado.

        Args:
            user_id: ID del usuario (employee_id)
            prompt_text: Texto del prompt a guardar

        Returns:
            SavedPrompt: El prompt guardado con su ID asignado

        Raises:
            ValueError: Si el prompt_text está vacío
        """
        if not prompt_text or not prompt_text.strip():
            raise ValueError("El texto del prompt no puede estar vacío")

        saved_prompt = SavedPrompt(user_id=user_id, prompt_text=prompt_text.strip())

        return self.repository.create(saved_prompt)
