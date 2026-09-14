import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from app.project.domain.gateway import ProjectAssignmentGateway
from app.project.domain.models import Project
from app.team.domain.models import PermissionLevel
from app.team.domain.repositories import TeamPermissionRepository
from app.users.domain.repositories import EmployeeGateway

logger = logging.getLogger(__name__)


@dataclass
class TeamMemberInfo:
    employee_odoo_id: int
    name: Optional[str]
    email: Optional[str]
    level: Optional[PermissionLevel]


@dataclass
class LedProjectTeam:
    project: Project
    members: List[TeamMemberInfo]


_VIEW_LEVELS = {PermissionLevel.view, PermissionLevel.validate}
_VALIDATE_LEVELS = {PermissionLevel.validate}

# Empleados ya logueados como "sin res.users": evita repetir el log en cada request.
_logged_no_user: Set[int] = set()

_CacheKey = Tuple[int, Optional[date], Optional[date]]


class TeamAccessService:
    """Resuelve equipos a partir de los proyectos gerenciados en Odoo y los cruza
    con los permisos locales.

    El equipo de un líder es SIEMPRE lo que Odoo devuelve en el momento
    (empleados con ``project.assignment`` vigente en los proyectos donde el
    líder es ``project.project.user_id``, ver ``get_led_team``). Los permisos
    locales sólo agregan capacidad de vista/validación a miembros puntuales de
    ese equipo y dejan de aplicar si Odoo ya no ubica a la persona bajo ese
    líder.
    """

    def __init__(
        self,
        employee_gateway: EmployeeGateway,
        project_assignment_gateway: ProjectAssignmentGateway,
        permission_repo: TeamPermissionRepository,
    ) -> None:
        self.employee_gateway = employee_gateway
        self.project_assignment_gateway = project_assignment_gateway
        self.permission_repo = permission_repo
        self._team_cache: Dict[_CacheKey, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Equipo por proyecto (en vivo, cacheado sólo durante el request)
    # ------------------------------------------------------------------
    def get_led_team(
        self,
        leader_employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Empleados asignados a proyectos gerenciados por ``leader_employee_id``.

        Lista vacía si la persona no gerencia proyectos o no tiene usuario Odoo.
        La vigencia de las asignaciones se evalúa contra ``[date_from, date_to]``
        (por defecto, la fecha actual si no se pasa ninguno).
        """
        cache_key: _CacheKey = (leader_employee_id, date_from, date_to)
        if cache_key in self._team_cache:
            return self._team_cache[cache_key]

        user_id = self.employee_gateway.get_user_id_by_employee_id(
            leader_employee_id
        )
        if user_id is None:
            # Normal para un miembro sin usuario Odoo. Sólo importa si la
            # persona debería liderar un equipo (ahí se verá como "equipo vacío").
            if leader_employee_id not in _logged_no_user:
                _logged_no_user.add(leader_employee_id)
                logger.info(
                    "El empleado %s no tiene res.users en Odoo: no se resuelve "
                    "equipo por proyecto (su acceso, si tiene, viene de un "
                    "permiso otorgado).",
                    leader_employee_id,
                )
            team: List[Dict[str, Any]] = []
        else:
            team = (
                self.project_assignment_gateway.get_team_users(
                    user_id, leader_employee_id, date_from, date_to
                )
                or []
            )
        self._team_cache[cache_key] = team
        return team

    def get_led_team_member_ids(self, leader_employee_id: int) -> Set[int]:
        return {u["id"] for u in self.get_led_team(leader_employee_id)}

    def is_leader(self, employee_id: int) -> bool:
        return bool(self.get_led_team_member_ids(employee_id))

    # ------------------------------------------------------------------
    # Permisos locales cruzados con el equipo por proyecto
    # ------------------------------------------------------------------
    def _granted_ids(
        self,
        member_employee_id: int,
        levels: Set[PermissionLevel],
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Set[int]:
        result: Set[int] = set()
        for perm in self.permission_repo.list_by_member(member_employee_id):
            if perm.level not in levels:
                continue
            leader_id = perm.leader_employee_odoo_id
            team_ids = {
                u["id"] for u in self.get_led_team(leader_id, date_from, date_to)
            }
            if member_employee_id not in team_ids:
                # El permiso dejó de aplicar: Odoo sacó a la persona del equipo.
                continue
            team_ids.discard(leader_id)
            team_ids.discard(member_employee_id)
            result |= team_ids
        return result

    def visible_employee_ids(
        self,
        employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Set[int]:
        """Empleados cuyas horas puede VER ``employee_id`` en la vista de equipo."""
        ids = {
            u["id"] for u in self.get_led_team(employee_id, date_from, date_to)
        }
        ids |= self._granted_ids(employee_id, _VIEW_LEVELS, date_from, date_to)
        return ids

    def validatable_employee_ids(
        self,
        employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Set[int]:
        """Empleados cuyas horas puede VALIDAR ``employee_id``.

        Nunca incluye al propio ``employee_id`` ni a sus líderes: no hay
        auto-aprobación ni aprobación hacia arriba.
        """
        ids = {
            u["id"] for u in self.get_led_team(employee_id, date_from, date_to)
        }
        ids |= self._granted_ids(employee_id, _VALIDATE_LEVELS, date_from, date_to)
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

        # Equipo propio (si gerencia proyectos en Odoo)
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

    # ------------------------------------------------------------------
    # Vista agrupada: proyectos gerenciados -> empleados asignados a cada uno
    # ------------------------------------------------------------------
    def get_led_team_by_project(
        self,
        leader_employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[LedProjectTeam]:
        """Proyectos que gerencia ``leader_employee_id``, con los empleados
        asignados a cada uno (excluyendo al propio líder).

        No cruza con permisos locales (``TeamMemberPermission``): esos siguen
        aplicando sólo a la vista plana (``get_led_team``/``visible_team_members``)
        y a ``validatable_employee_ids``.
        """
        user_id = self.employee_gateway.get_user_id_by_employee_id(
            leader_employee_id
        )
        if user_id is None:
            return []

        projects = self.project_assignment_gateway.get_managed_projects(user_id)
        if not projects:
            return []

        assignments = self.project_assignment_gateway.get_project_assignments(
            [p.id for p in projects], date_from, date_to
        )

        employee_ids = {
            a["employee_id"][0]
            for a in assignments
            if a.get("employee_id") and a["employee_id"][0] != leader_employee_id
        }
        employees_by_id: Dict[int, Any] = {}
        if employee_ids:
            employees_by_id = {
                e.id: e for e in self.employee_gateway.get_by_ids(list(employee_ids))
            }

        members_by_project: Dict[int, List[TeamMemberInfo]] = defaultdict(list)
        for a in assignments:
            employee = a.get("employee_id")
            project = a.get("project_id")
            if not employee or not project:
                continue
            employee_id = employee[0]
            project_id = project[0]
            if employee_id == leader_employee_id:
                continue
            emp = employees_by_id.get(employee_id)
            members_by_project[project_id].append(
                TeamMemberInfo(
                    employee_odoo_id=employee_id,
                    name=emp.full_name if emp else None,
                    email=emp.email if emp else None,
                    level=None,
                )
            )

        return [
            LedProjectTeam(project=p, members=members_by_project.get(p.id, []))
            for p in projects
        ]
