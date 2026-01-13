from datetime import datetime
from typing import Optional


class SavedPrompt:
    """Entidad de dominio para prompts guardados del agente."""

    def __init__(
        self,
        user_id: int,
        prompt_text: str,
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.prompt_text = prompt_text
        self.created_at = created_at or datetime.now()

    def __repr__(self) -> str:
        return f"<SavedPrompt(id={self.id}, user_id={self.user_id}, prompt='{self.prompt_text[:50]}...')>"
