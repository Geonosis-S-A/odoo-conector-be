from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Optional


class PermissionLevel(StrEnum):
    """Nivel de acceso que un líder le otorga a un miembro de su equipo Odoo."""

    view = "view"  # ver las horas de todo el equipo
    validate = "validate"  # ver y validar las horas del equipo


@dataclass
class TeamMemberPermission:
    """Permiso puntual que un líder concede a un miembro.

    El equipo en sí NO se persiste: es siempre la jerarquía de Odoo en vivo.
    Esta fila sólo agrega capacidad de vista/validación y deja de aplicar
    automáticamente si Odoo saca al miembro del equipo de ese líder.
    """

    id: Optional[int]
    leader_employee_odoo_id: int
    member_employee_odoo_id: int
    level: PermissionLevel
    created_at: Optional[datetime] = None
