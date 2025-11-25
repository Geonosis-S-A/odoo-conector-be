from abc import ABC, abstractmethod
from typing import List
from app.saved_prompts.domain.models import SavedPrompt


class SavedPromptRepository(ABC):
    """Interface del repositorio para prompts guardados."""

    @abstractmethod
    def create(self, saved_prompt: SavedPrompt) -> SavedPrompt:
        """Crea un nuevo prompt guardado.

        Args:
            saved_prompt: El prompt a guardar

        Returns:
            SavedPrompt: El prompt guardado con su ID asignado
        """
        pass

    @abstractmethod
    def list_by_user(self, user_id: int) -> List[SavedPrompt]:
        """Lista todos los prompts guardados de un usuario.

        Args:
            user_id: ID del usuario (employee_id)

        Returns:
            List[SavedPrompt]: Lista de prompts del usuario
        """
        pass

    @abstractmethod
    def delete(self, prompt_id: int, user_id: int) -> bool:
        """Elimina un prompt guardado.

        Args:
            prompt_id: ID del prompt a eliminar
            user_id: ID del usuario (para validar ownership)

        Returns:
            bool: True si se eliminó correctamente

        Raises:
            ValueError: Si el prompt no existe o no pertenece al usuario
        """
        pass

    @abstractmethod
    def get_by_id(self, prompt_id: int) -> SavedPrompt | None:
        """Obtiene un prompt por su ID.

        Args:
            prompt_id: ID del prompt

        Returns:
            SavedPrompt | None: El prompt o None si no existe
        """
        pass
