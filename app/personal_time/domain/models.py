# Entidades del dominio para personal_time, desacopladas del ORM

from dataclasses import dataclass


@dataclass
class LeaveType:
    """Representa un tipo de licencia/ausencia en el sistema."""
    
    id: int
    name: str

    @classmethod
    def from_odoo_data(cls, odoo_data: dict) -> "LeaveType":
        """Crea un LeaveType desde los datos de Odoo.
        
        Args:
            odoo_data: Diccionario con datos de Odoo que debe contener 'id' y 'name'
            
        Returns:
            LeaveType: Instancia del tipo de licencia
        """
        return cls(
            id=odoo_data["id"],
            name=odoo_data["name"]
        )
