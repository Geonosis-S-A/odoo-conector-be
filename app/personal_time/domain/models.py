# Entidades del dominio para personal_time, desacopladas del ORM

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class TimeOffType:
    """Representa un tipo de licencia/ausencia en el sistema."""
    
    id: int
    name: str

    @classmethod
    def from_odoo_data(cls, odoo_data: dict) -> "TimeOffType":
        """Crea un TimeOffType desde los datos de Odoo.
        
        Args:
            odoo_data: Diccionario con datos de Odoo que debe contener 'id' y 'name'
            
        Returns:
            TimeOffType: Instancia del tipo de licencia
        """
        return cls(
            id=odoo_data["id"],
            name=odoo_data["name"]
        )


@dataclass
class TimeOffRequest:
    """Representa una solicitud de licencia/ausencia."""
    
    holiday_status_id: int  # ID del tipo de licencia
    name: str  # Descripción/motivo
    request_date_from: date  # Fecha de inicio
    request_date_to: date  # Fecha de fin
    employee_id: int  # ID del empleado

    def to_odoo_data(self) -> dict:
        """Convierte la solicitud a formato de Odoo.
        
        Returns:
            dict: Datos en formato esperado por Odoo hr.leave
        """
        return {
            "holiday_status_id": self.holiday_status_id,
            "name": self.name,
            "request_date_from": self.request_date_from.strftime("%Y-%m-%d"),
            "request_date_to": self.request_date_to.strftime("%Y-%m-%d"),
            "employee_id": self.employee_id,
        }


@dataclass
class TimeOffRequestResult:
    """Representa el resultado de crear una solicitud de licencia."""
    
    request_id: Optional[int]
    success: bool
    message: str

    @classmethod
    def success_result(cls, request_id: int) -> "TimeOffRequestResult":
        """Crea un resultado exitoso."""
        return cls(
            request_id=request_id,
            success=True,
            message=f"Solicitud creada exitosamente con ID: {request_id}"
        )

    @classmethod
    def error_result(cls, error_message: str) -> "TimeOffRequestResult":
        """Crea un resultado de error."""
        return cls(
            request_id=None,
            success=False,
            message=f"Error al crear solicitud: {error_message}"
        )
