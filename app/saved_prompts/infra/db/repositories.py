from typing import List
from sqlmodel import Session, select, col
from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository
from app.saved_prompts.infra.db.models import SavedPromptModel


class SQLModelSavedPromptRepository(SavedPromptRepository):
    """Implementación del repositorio usando SQLModel."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, saved_prompt: SavedPrompt) -> SavedPrompt:
        """Crea un nuevo prompt guardado en la base de datos."""
        db_prompt = SavedPromptModel(
            user_id=saved_prompt.user_id,
            prompt_text=saved_prompt.prompt_text,
            created_at=saved_prompt.created_at,
        )

        self.session.add(db_prompt)
        self.session.commit()
        self.session.refresh(db_prompt)

        # Convertir de modelo DB a entidad de dominio
        return self._to_domain(db_prompt)

    def list_by_user(self, user_id: int) -> List[SavedPrompt]:
        """Lista todos los prompts de un usuario, ordenados por fecha de creación (más recientes primero)."""
        statement = (
            select(SavedPromptModel)
            .where(SavedPromptModel.user_id == user_id)
            .order_by(col(SavedPromptModel.created_at).desc())
        )

        results = self.session.exec(statement).all()
        return [self._to_domain(db_prompt) for db_prompt in results]

    def delete(self, prompt_id: int, user_id: int) -> bool:
        """Elimina un prompt si pertenece al usuario."""
        statement = select(SavedPromptModel).where(
            SavedPromptModel.id == prompt_id, SavedPromptModel.user_id == user_id
        )

        db_prompt = self.session.exec(statement).first()

        if not db_prompt:
            raise ValueError(
                f"Prompt con ID {prompt_id} no existe o no pertenece al usuario"
            )

        self.session.delete(db_prompt)
        self.session.commit()
        return True

    def get_by_id(self, prompt_id: int) -> SavedPrompt | None:
        """Obtiene un prompt por su ID."""
        statement = select(SavedPromptModel).where(SavedPromptModel.id == prompt_id)
        db_prompt = self.session.exec(statement).first()

        if not db_prompt:
            return None

        return self._to_domain(db_prompt)

    def _to_domain(self, db_prompt: SavedPromptModel) -> SavedPrompt:
        """Convierte un modelo de DB a entidad de dominio."""
        return SavedPrompt(
            id=db_prompt.id,
            user_id=db_prompt.user_id,
            prompt_text=db_prompt.prompt_text,
            created_at=db_prompt.created_at,
        )
