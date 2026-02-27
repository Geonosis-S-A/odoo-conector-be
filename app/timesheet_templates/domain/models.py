from datetime import datetime
from typing import Optional


class TimesheetTemplate:
    """Entidad de dominio para templates de carga de timesheets."""

    def __init__(
        self,
        user_id: int,
        name: str,
        project_id: int,
        task_id: Optional[int] = None,
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.project_id = project_id
        self.task_id = task_id
        self.created_at = created_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<TimesheetTemplate(id={self.id}, user_id={self.user_id}, "
            f"name='{self.name}', project_id={self.project_id}, task_id={self.task_id})>"
        )
