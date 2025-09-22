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
    name: Optional[str]  # Descripción/motivo
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
            "name": self.name or "",
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


@dataclass
class TimeOffRequestInfo:
    """Representa información de una solicitud de tiempo personal existente."""
    
    id: int
    holiday_status_id: int
    holiday_status_name: str
    name: Optional[str]  # Descripción/motivo
    request_date_from: date
    request_date_to: date
    employee_id: int
    employee_name: str
    state: str  # Estado de la solicitud (draft, confirm, validate, refuse, cancel)
    number_of_days: float

    @classmethod
    def from_odoo_data(cls, odoo_data: dict) -> "TimeOffRequestInfo":
        """Crea un TimeOffRequestInfo desde los datos de Odoo.
        
        Args:
            odoo_data: Diccionario con datos de Odoo hr.leave
            
        Returns:
            TimeOffRequestInfo: Instancia de la solicitud
        """
        # Manejo de fechas que pueden venir en diferentes formatos
        date_from = odoo_data["request_date_from"]
        date_to = odoo_data["request_date_to"]
        
        if isinstance(date_from, str):
            date_from = date.fromisoformat(date_from.split(' ')[0])  # Tomar solo la fecha si viene con hora
        
        if isinstance(date_to, str):
            date_to = date.fromisoformat(date_to.split(' ')[0])
        
        # Manejar campos que pueden ser False en Odoo en lugar de None o cadenas vacías
        def safe_string_value(value, default=""):
            """Convierte valores de Odoo a string, manejando False y None."""
            if value is False or value is None:
                return default
            return str(value)

        # Extraer valores de campos many2one de forma segura
        holiday_status_id = odoo_data["holiday_status_id"][0] if isinstance(odoo_data["holiday_status_id"], list) else odoo_data["holiday_status_id"]
        holiday_status_name = odoo_data["holiday_status_id"][1] if isinstance(odoo_data["holiday_status_id"], list) else odoo_data.get("holiday_status_name", "")
        
        employee_id = odoo_data["employee_id"][0] if isinstance(odoo_data["employee_id"], list) else odoo_data["employee_id"]
        employee_name = odoo_data["employee_id"][1] if isinstance(odoo_data["employee_id"], list) else odoo_data.get("employee_name", "")

        return cls(
            id=odoo_data["id"],
            holiday_status_id=holiday_status_id,
            holiday_status_name=safe_string_value(holiday_status_name),
            name=safe_string_value(odoo_data.get("name")),
            request_date_from=date_from,
            request_date_to=date_to,
            employee_id=employee_id,
            employee_name=safe_string_value(employee_name),
            state=safe_string_value(odoo_data.get("state", "draft")),
            number_of_days=float(odoo_data.get("number_of_days", 0))
        )
