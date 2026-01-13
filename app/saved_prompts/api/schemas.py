from datetime import datetime
from pydantic import BaseModel, Field


class CreateSavedPromptRequest(BaseModel):
    """Schema para crear un prompt guardado."""

    prompt_text: str = Field(
        ..., description="Texto del prompt a guardar", min_length=1
    )


class UpdateSavedPromptRequest(BaseModel):
    """Schema para actualizar un prompt guardado."""

    prompt_text: str = Field(..., description="Nuevo texto del prompt", min_length=1)


class SavedPromptResponse(BaseModel):
    """Schema de respuesta para un prompt guardado."""

    id: int = Field(..., description="ID del prompt guardado")
    user_id: int = Field(..., description="ID del usuario propietario")
    prompt_text: str = Field(..., description="Texto del prompt")
    created_at: datetime = Field(..., description="Fecha de creación")

    class Config:
        from_attributes = True
