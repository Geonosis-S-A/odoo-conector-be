import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from app.team.domain.models import PermissionLevel
from app.team.domain.repositories import TeamPermissionRepository
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway

logger = logging.getLogger(__name__)


@dataclass
class TeamMemberInfo:
    employee_odoo_id: int
    name: Optional[str]
    email: Optional[str]
    level: Optional[PermissionLevel]


_VIEW_LEVELS = {PermissionLevel.view, PermissionLevel.validate}
_VALIDATE_LEVELS = {PermissionLevel.validate}


class TeamAccessService:
    """Resuelve equipos desde la jerarquía de Odoo y los cruza con los permisos locales.

    El equipo de un líder es SIEMPRE lo que Odoo devuelve en el momento
    (``get_team_users``). Los permisos locales sólo agregan capacidad de
    vista/validación a miembros puntuales de ese equipo y dejan de aplicar
    si Odoo ya no ubica a la persona bajo ese líder.
    """

    def __init__(
        self,
        employee_gateway: EmployeeGateway,
        timesheet_line_gateway: TimesheetLineGateway,
        permission_repo: TeamPermissionRepository,
    ) -> None:
        self.employee_gateway = employee_gateway
        self.timesheet_line_gateway = timesheet_line_gateway
        self.permission_repo = permission_repo
        self._team_cache: Dict[int, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Jerarquía de Odoo (en vivo, cacheada sólo durante el request)
    # ------------------------------------------------------------------
    def get_led_team(self, leader_employee_id: int) -> List[Dict[str, Any]]:
        """Empleados del equipo Odoo de ``leader_employee_id``.

        Lista vacía si la persona no lidera a nadie o no tiene usuario Odoo.
        """
        if leader_employee_id in self._team_cache:
            return self._team_cache[leader_employee_id]

        user_id = self.employee_gateway.get_user_id_by_employee_id(
            leader_employee_id
        )
        if user_id is None:
            logger.warning(
                "El empleado %s no tiene res.users vinculado en Odoo; su "
                "equipo se resolverá vacío (no podrá ver ni validar equipo).",
                leader_employee_id,
            )
            team: List[Dict[str, Any]] = []
        else:
            team = (
                self.timesheet_line_gateway.get_team_users(
                    user_id, leader_employee_id
                )
                or []
            )
        self._team_cache[leader_employee_id] = team
        return team

    def get_led_team_member_ids(self, leader_employee_id: int) -> Set[int]:
        return {u["id"] for u in self.get_led_team(leader_employee_id)}

    def is_leader(self, employee_id: int) -> bool:
        return bool(self.get_led_team_member_ids(employee_id))

    # ------------------------------------------------------------------
    # Permisos locales cruzados con la jerarquía
    # ------------------------------------------------------------------
    def _granted_ids(
        self, member_employee_id: int, levels: Set[PermissionLevel]
    ) -> Set[int]:
        result: Set[int] = set()
        for perm in self.permission_repo.list_by_member(member_employee_id):
            if perm.level not in levels:
                continue
            leader_id = perm.leader_employee_odoo_id
            team_ids = self.get_led_team_member_ids(leader_id)
            if member_employee_id not in team_ids:
                # El permiso dejó de aplicar: Odoo sacó a la persona del equipo.
                continue
            team_ids.discard(leader_id)
            team_ids.discard(member_employee_id)
            result |= team_ids
        return result

    def visible_employee_ids(self, employee_id: int) -> Set[int]:
        """Empleados cuyas horas puede VER ``employee_id`` en la vista de equipo."""
        ids = self.get_led_team_member_ids(employee_id)
        ids |= self._granted_ids(employee_id, _VIEW_LEVELS)
        return ids

    def validatable_employee_ids(self, employee_id: int) -> Set[int]:
        """Empleados cuyas horas puede VALIDAR ``employee_id``.

        Nunca incluye al propio ``employee_id`` ni a sus líderes: no hay
        auto-aprobación ni aprobación hacia arriba.
        """
        ids = self.get_led_team_member_ids(employee_id)
        ids |= self._granted_ids(employee_id, _VALIDATE_LEVELS)
        ids.discard(employee_id)
        return ids

    def can_view_team(self, employee_id: int) -> bool:
        return bool(self.visible_employee_ids(employee_id))

    def can_validate_team(self, employee_id: int) -> bool:
        return bool(self.validatable_employee_ids(employee_id))

    def visible_team_members(self, employee_id: int) -> List[TeamMemberInfo]:
        """Miembros (id + nombre + email) cuyas horas puede VER ``employee_id``.

        Mismo conjunto que ``visible_employee_ids`` pero con los datos de
        cada persona (para pintar la lista en el front). ``level`` va siempre
        en None: acá no se administran permisos.
        """
        by_id: Dict[int, TeamMemberInfo] = {}

        def _add(u: Dict[str, Any]) -> None:
            eid = u["id"]
            if eid == employee_id or eid in by_id:
                return
            by_id[eid] = TeamMemberInfo(
                employee_odoo_id=eid,
                name=u.get("name"),
                email=u.get("work_email") or None,
                level=None,
            )

        # Equipo propio (si lidera en Odoo)
        for u in self.get_led_team(employee_id):
            _add(u)

        # Equipos donde tiene permiso como miembro
        for perm in self.permission_repo.list_by_member(employee_id):
            leader_id = perm.leader_employee_odoo_id
            team = self.get_led_team(leader_id)
            if employee_id not in {u["id"] for u in team}:
                # El permiso dejó de aplicar: Odoo sacó a la persona del equipo.
                continue
            for u in team:
                if u["id"] == leader_id:
                    continue
                _add(u)

        return list(by_id.values())
