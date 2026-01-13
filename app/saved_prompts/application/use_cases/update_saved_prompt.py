from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository


class UpdateSavedPromptUseCase:
    """Caso de uso para actualizar un prompt guardado."""

    def __init__(self, repository: SavedPromptRepository):
        self.repository = repository

    def execute(
        self, prompt_id: int, user_id: int, new_prompt_text: str
    ) -> SavedPrompt:
        """Actualiza el texto de un prompt guardado.

        Args:
            prompt_id: ID del prompt a actualizar
            user_id: ID del usuario (para validar ownership)
            new_prompt_text: Nuevo texto del prompt

        Returns:
            SavedPrompt: El prompt actualizado

        Raises:
            ValueError: Si el prompt_text está vacío, el prompt no existe,
                       o no pertenece al usuario
        """
        # Validar que el texto no esté vacío
        if not new_prompt_text or not new_prompt_text.strip():
            raise ValueError("El texto del prompt no puede estar vacío")

        # Obtener el prompt existente
        existing_prompt = self.repository.get_by_id(prompt_id)

        if not existing_prompt:
            raise ValueError(f"Prompt con ID {prompt_id} no existe")

        # Verificar que el prompt pertenece al usuario
        if existing_prompt.user_id != user_id:
            raise ValueError(
                f"Prompt con ID {prompt_id} no pertenece al usuario {user_id}"
            )

        # Actualizar el texto
        existing_prompt.prompt_text = new_prompt_text.strip()

        # Guardar cambios
        return self.repository.update(existing_prompt)
