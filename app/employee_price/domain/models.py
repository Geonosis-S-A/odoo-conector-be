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
    date_from: date
    cost_per_hour: Optional[float] = None
    date_to: Optional[date] = None

    @classmethod
    def from_request(
        cls,
        user_id: int,
        date_from: date,
        cost_per_hour: Optional[float] = None,
        date_to: Optional[date] = None,
    ) -> "EmployeePrice":
        """Crea una instancia desde datos de request"""
        return cls(
            id=None,
            user_id=user_id,
            date_from=date_from,
            cost_per_hour=cost_per_hour,
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

