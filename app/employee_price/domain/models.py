from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class EmployeePrice:
    """
    Entidad de dominio que representa el precio por hora de un empleado.
    Incluye vigencia temporal (date_from, date_to).
    """

    id: Optional[int]
    user_id: int
    email: str
    full_name: str
    cost_per_hour: float
    date_from: date
    date_to: Optional[date] = None

    @classmethod
    def from_request(
        cls,
        user_id: int,
        email: str,
        full_name: str,
        cost_per_hour: float,
        date_from: date,
        date_to: Optional[date] = None,
    ) -> "EmployeePrice":
        """Crea una instancia desde datos de request"""
        return cls(
            id=None,
            user_id=user_id,
            email=email,
            full_name=full_name,
            cost_per_hour=cost_per_hour,
            date_from=date_from,
            date_to=date_to,
        )

    def is_active_on(self, check_date: date) -> bool:
        """Verifica si el precio está activo en una fecha determinada"""
        if check_date < self.date_from:
            return False
        if self.date_to and check_date > self.date_to:
            return False
        return True

    def is_currently_active(self) -> bool:
        """Verifica si el precio está activo actualmente"""
        from datetime import date as date_module

        return self.is_active_on(date_module.today())

