from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CreateTimesheetTemplateRequest(BaseModel):
    """Schema para crear un template de carga de timesheet."""

    name: str = Field(
        ..., description="Nombre descriptivo del template", min_length=1, max_length=100
    )
    project_id: int = Field(..., description="ID del proyecto en Odoo")
    task_id: Optional[int] = Field(
        default=None, description="ID de la tarea en Odoo (opcional)"
    )


class TimesheetTemplateResponse(BaseModel):
    """Schema de respuesta para un template de carga de timesheet."""

    id: int = Field(..., description="ID del template")
    user_id: int = Field(..., description="ID del usuario propietario")
    name: str = Field(..., description="Nombre descriptivo del template")
    project_id: int = Field(..., description="ID del proyecto en Odoo")
    task_id: Optional[int] = Field(
        default=None, description="ID de la tarea en Odoo (opcional)"
    )
    created_at: datetime = Field(..., description="Fecha de creación")

    class Config:
        from_attributes = True
