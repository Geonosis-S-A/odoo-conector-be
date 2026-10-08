import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from app.project.domain.gateway import ProjectAssignmentGateway
from app.project.domain.models import Project
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


@dataclass
class LedProjectTeam:
    project: Project
    members: List[TeamMemberInfo]
    # Pendientes del mes actual (día 1 a hoy) y de fechas anteriores al día 1.
    pending_count: int = 0
    pending_previous_count: int = 0
    approver_names: List[str] = field(default_factory=list)


_VIEW_LEVELS = {PermissionLevel.view, PermissionLevel.validate}
_VALIDATE_LEVELS = {PermissionLevel.validate}

# Empleados ya logueados como "sin res.users": evita repetir el log en cada request.
_logged_no_user: Set[int] = set()

_CacheKey = Tuple[int, Optional[date], Optional[date]]


class TeamAccessService:
    """Resuelve equipos a partir de Odoo y los cruza con los permisos locales.

    El equipo de un líder es SIEMPRE lo que Odoo devuelve en el momento (ver
    ``get_led_team``): la unión de la jerarquía (``timesheet_manager_id``/
    ``child_of`` sobre ``parent_id``) y los proyectos que gerencia
    (``project.assignment`` vigente en proyectos donde es
    ``project.project.user_id``). Se mantiene la jerarquía activa junto con
    proyectos porque la asignación por proyecto todavía tiene poca cobertura
    en Odoo. Los permisos locales sólo agregan capacidad de vista/validación
    a miembros puntuales de ese equipo y dejan de aplicar si Odoo ya no ubica
    a la persona bajo ese líder.
    """

    def __init__(
        self,
        employee_gateway: EmployeeGateway,
        project_assignment_gateway: ProjectAssignmentGateway,
        timesheet_line_gateway: TimesheetLineGateway,
        permission_repo: TeamPermissionRepository,
    ) -> None:
        self.employee_gateway = employee_gateway
        self.project_assignment_gateway = project_assignment_gateway
        self.timesheet_line_gateway = timesheet_line_gateway
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
        """Empleados que ``leader_employee_id`` lidera en Odoo: jerarquía ∪ proyectos.

        Lista vacía si la persona no lidera a nadie por ninguno de los dos
        criterios, o no tiene usuario Odoo. La vigencia de las asignaciones
        por proyecto se evalúa contra ``[date_from, date_to]`` (por defecto,
        la fecha actual si no se pasa ninguno); la jerarquía no tiene noción
        de vigencia por fecha.
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
                    "equipo (su acceso, si tiene, viene de un permiso otorgado).",
                    leader_employee_id,
                )
            team: List[Dict[str, Any]] = []
        else:
            project_team = (
                self.project_assignment_gateway.get_team_users(
                    user_id,
                    leader_employee_id,
                    date_from,
                    date_to,
                    only_active=True,
                )
                or []
            )
            # Un PM "puro" (PM de proyectos y gerente de ninguno) ve sólo a
            # quienes cargan en sus proyectos, no a su equipo por jerarquía.
            hierarchy_team = (
                []
                if self.project_assignment_gateway.is_project_manager_only(user_id)
                else (
                    self.timesheet_line_gateway.get_team_users(
                        user_id, leader_employee_id
                    )
                    or []
                )
            )
            by_id: Dict[int, Dict[str, Any]] = {}
            for u in project_team + hierarchy_team:
                by_id[u["id"]] = u
            team = list(by_id.values())
        self._team_cache[cache_key] = team
        return team

    def get_led_team_member_ids(self, leader_employee_id: int) -> Set[int]:
        return {u["id"] for u in self.get_led_team(leader_employee_id)}

    # ------------------------------------------------------------------
    # Equipo acotado a UN proyecto puntual (solo project.assignment, sin
    # jerarquía): para la validación "por proyecto", distinta de la vista
    # plana de equipo.
    # ------------------------------------------------------------------
    def manages_project(self, leader_employee_id: int, project_id: int) -> bool:
        """True si ``leader_employee_id`` es gerente o Project Manager de
        ``project_id`` en Odoo."""
        user_id = self.employee_gateway.get_user_id_by_employee_id(
            leader_employee_id
        )
        if user_id is None:
            return False
        managed = self.project_assignment_gateway.get_led_projects(user_id)
        return any(p.id == project_id for p in managed)

    def project_assigned_employee_ids(
        self,
        project_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Set[int]:
        """Empleados con ``project.assignment`` vigente en ``project_id``.

        A diferencia de ``get_led_team``, esto NO mira jerarquía: es
        exclusivamente quién fue asignado a ESE proyecto puntual.
        """
        assignments = self.project_assignment_gateway.get_project_assignments(
            [project_id], date_from, date_to
        )
        return {
            a["employee_id"][0] for a in assignments if a.get("employee_id")
        }

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

    # ------------------------------------------------------------------
    # Autoridad POR LÍNEA: validar/borrar según el gerente del proyecto
    # ------------------------------------------------------------------
    def _authorities(self, actor_employee_id: int) -> List[Tuple[int, int]]:
        """Pares ``(employee_id, user_id)`` con cuya autoridad actúa el actor:
        él mismo y los líderes que le delegaron ``validate`` (mientras Odoo
        siga ubicándolo en el equipo de ese líder)."""
        authorities: List[Tuple[int, int]] = []
        own_user = self.employee_gateway.get_user_id_by_employee_id(
            actor_employee_id
        )
        if own_user is not None:
            authorities.append((actor_employee_id, own_user))

        for perm in self.permission_repo.list_by_member(actor_employee_id):
            if perm.level not in _VALIDATE_LEVELS:
                continue
            leader_id = perm.leader_employee_odoo_id
            if actor_employee_id not in {u["id"] for u in self.get_led_team(leader_id)}:
                continue
            leader_user = self.employee_gateway.get_user_id_by_employee_id(leader_id)
            if leader_user is not None:
                authorities.append((leader_id, leader_user))
        return authorities

    def lines_authority(
        self, actor_employee_id: int, lines: List[Tuple[int, int]]
    ) -> Dict[Tuple[int, int], bool]:
        """Para cada ``(employee_id, project_id)`` de una línea, si el actor
        puede validarla/borrarla.

        Regla: el Project Manager (``x_project_manager_id``) o el gerente
        (``project.project.user_id``) del proyecto: cualquiera de los dos.
        Si el proyecto no tiene ninguno, el jefe por jerarquía del empleado.
        Nunca sobre las propias horas ni (vía permiso delegado) sobre las del
        líder que delegó. Una sola lectura de aprobadores por llamada.
        """
        pairs = set(lines)
        if not pairs:
            return {}
        authorities = self._authorities(actor_employee_id)
        if not authorities:
            return {pair: False for pair in pairs}

        approvers = self.project_assignment_gateway.get_project_approvers(
            sorted({project_id for _, project_id in pairs})
        )
        hierarchy_cache: Dict[int, Set[int]] = {}

        def _hierarchy(leader_id: int, leader_user: int) -> Set[int]:
            if leader_id not in hierarchy_cache:
                hierarchy_cache[leader_id] = {
                    u["id"]
                    for u in (
                        self.timesheet_line_gateway.get_team_users(
                            leader_user, leader_id
                        )
                        or []
                    )
                }
            return hierarchy_cache[leader_id]

        result: Dict[Tuple[int, int], bool] = {}
        for employee_id, project_id in pairs:
            allowed = False
            if employee_id != actor_employee_id:
                approver_users = {u for u, _ in approvers.get(project_id, [])}
                for leader_id, leader_user in authorities:
                    if employee_id == leader_id:
                        continue
                    if approver_users:
                        if leader_user in approver_users:
                            allowed = True
                            break
                    elif employee_id in _hierarchy(leader_id, leader_user):
                        allowed = True
                        break
            result[(employee_id, project_id)] = allowed
        return result

    def project_approver_names(self, project_ids: List[int]) -> Dict[int, List[str]]:
        """Nombres de quienes pueden aprobar las horas de cada proyecto (PM y
        gerente), para mostrar quién debe aprobarlas."""
        approvers = self.project_assignment_gateway.get_project_approvers(
            sorted(set(project_ids))
        )
        return {
            project_id: [name for _, name in users]
            for project_id, users in approvers.items()
        }

    def can_act_on_line(
        self, actor_employee_id: int, line_employee_id: int, line_project_id: int
    ) -> bool:
        pair = (line_employee_id, line_project_id)
        return self.lines_authority(actor_employee_id, [pair]).get(pair, False)

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

        projects = self.project_assignment_gateway.get_led_projects(user_id)
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
        # Pares (employee_id, project_id) realmente asignados, para no
        # contar pendientes de alguien que no está asignado a ESE proyecto
        # (p.ej. validable por jerarquía en otro contexto).
        assigned_pairs: Set[Tuple[int, int]] = set()
        for a in assignments:
            employee = a.get("employee_id")
            project = a.get("project_id")
            if not employee or not project:
                continue
            employee_id = employee[0]
            project_id = project[0]
            if employee_id == leader_employee_id:
                continue
            assigned_pairs.add((employee_id, project_id))
            emp = employees_by_id.get(employee_id)
            members_by_project[project_id].append(
                TeamMemberInfo(
                    employee_odoo_id=employee_id,
                    name=emp.full_name if emp else None,
                    email=emp.email if emp else None,
                    level=None,
                )
            )

        month_start = date.today().replace(day=1)
        pending_count_by_project: Dict[int, int] = defaultdict(int)
        pending_previous_by_project: Dict[int, int] = defaultdict(int)
        if assigned_pairs:
            pending_lines = self.timesheet_line_gateway.get_pending_lines_minimal(
                list(employee_ids), [p.id for p in projects]
            )
            for line in pending_lines:
                employee = line.get("employee_id")
                project = line.get("project_id")
                if not employee or not project:
                    continue
                pair = (employee[0], project[0])
                if pair not in assigned_pairs:
                    continue
                line_date = line.get("date")
                if line_date and date.fromisoformat(str(line_date)[:10]) < month_start:
                    pending_previous_by_project[pair[1]] += 1
                else:
                    pending_count_by_project[pair[1]] += 1

        approver_names = self.project_approver_names([p.id for p in projects])
        return [
            LedProjectTeam(
                project=p,
                approver_names=approver_names.get(p.id, []),
                members=members_by_project.get(p.id, []),
                pending_count=pending_count_by_project.get(p.id, 0),
                pending_previous_count=pending_previous_by_project.get(p.id, 0),
            )
            for p in projects
        ]
