from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class TimesheetTemplateModel(SQLModel, table=True):
    """Modelo de base de datos para templates de carga de timesheets."""

    __tablename__ = "timesheettemplate"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        index=True, description="ID del usuario que creó el template"
    )
    name: str = Field(description="Nombre descriptivo del template")
    project_id: int = Field(description="ID del proyecto en Odoo")
    task_id: Optional[int] = Field(
        default=None, description="ID de la tarea en Odoo (opcional)"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Fecha de creación"
    )
