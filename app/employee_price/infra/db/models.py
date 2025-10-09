from datetime import datetime, UTC, date
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import event
from app.users.infra.db.models import UserModel


class EmployeePriceModel(SQLModel, table=True):
    """
    Modelo de base de datos para employee_price.
    Almacena el precio por hora de un empleado con vigencia temporal.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="usermodel.id", index=True)
    date_from: date = Field(index=True, description="Fecha de inicio de vigencia")
    cost_per_hour: Optional[float] = Field(
        default=None, gt=0, description="Costo por hora del empleado (opcional, debe ser mayor a 0 si se proporciona)"
    )
    date_to: Optional[date] = Field(
        default=None, index=True, description="Fecha de fin de vigencia (opcional)"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relación con el usuario
    user: Optional["UserModel"] = Relationship()

