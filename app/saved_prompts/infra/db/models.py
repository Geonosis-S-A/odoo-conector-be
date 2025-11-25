from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class SavedPromptModel(SQLModel, table=True):
    """Modelo de base de datos para prompts guardados."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        index=True, description="ID del usuario (employee_id) que guardó el prompt"
    )
    prompt_text: str = Field(description="Texto del prompt guardado")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Fecha de creación"
    )
