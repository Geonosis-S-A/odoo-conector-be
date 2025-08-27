from datetime import datetime, UTC, timedelta
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from app.users.infra.db.models import UserModel


def default_ttl():
    return datetime.now(UTC) + timedelta(days=15)


class TimesheetLineNotificationModel(SQLModel, table=True):
    """
    Tabla para registrar notificaciones de corrección de timesheet_line.
    timesheet_line_id es solo una referencia a Odoo, no foreign key.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    timesheet_line_id: int = Field(
        index=True, description="ID de timesheet_line en Odoo"
    )
    approver_id: int = Field(foreign_key="usermodel.id", index=True)
    receiver_id: int = Field(foreign_key="usermodel.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ttl: Optional[datetime] = Field(
        default_factory=default_ttl,
        description="Hasta cuándo es válida la notificación",
    )

    # Relaciones opcionales (puedes omitirlas si no las necesitas)
    sender: Optional["UserModel"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[TimesheetLineNotificationModel.approver_id]"
        }
    )
    receiver: Optional["UserModel"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[TimesheetLineNotificationModel.receiver_id]"
        }
    )
