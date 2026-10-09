from dataclasses import dataclass
from datetime import date, datetime
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

    ``valid_from``/``valid_until`` acotan la vigencia (ambos inclusive), p. ej.
    para cubrir las aprobaciones mientras el líder está de vacaciones. Sin
    fechas el permiso no vence. Fuera de la vigencia no concede nada.
    """

    id: Optional[int]
    leader_employee_odoo_id: int
    member_employee_odoo_id: int
    level: PermissionLevel
    created_at: Optional[datetime] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None

    def is_active(self, on: date) -> bool:
        """True si el permiso está vigente el día ``on``."""
        if self.valid_from is not None and on < self.valid_from:
            return False
        if self.valid_until is not None and on > self.valid_until:
            return False
        return True
