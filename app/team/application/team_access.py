import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.project.domain.gateway import ProjectAssignmentGateway
from app.project.domain.models import Project
from app.shared.utils.step_timer import StepTimer
from app.shared.utils.ttl_cache import TtlCache
from app.team.domain.models import PermissionLevel, TeamMemberPermission
from app.team.domain.repositories import TeamPermissionRepository
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway

logger = logging.getLogger(__name__)

# Cachés de proceso (el servicio se instancia por request, por eso van a nivel
# de módulo). TTL en AUTHZ_CACHE_TTL_SECONDS; 0 las desactiva.
_USER_ID_CACHE = TtlCache(settings.AUTHZ_CACHE_TTL_SECONDS)  # employee_id -> user_id
_LED_PROJECTS_CACHE = TtlCache(settings.AUTHZ_CACHE_TTL_SECONDS)  # user_id -> proyectos
_APPROVERS_CACHE = TtlCache(settings.AUTHZ_CACHE_TTL_SECONDS)  # project_id -> aprobadores
_COVERAGE_CACHE = TtlCache(settings.AUTHZ_CACHE_TTL_SECONDS)  # employee_id -> [Coverage]


@dataclass
class TeamMemberInfo:
    employee_odoo_id: int
    name: Optional[str]
    email: Optional[str]
    level: Optional[PermissionLevel]
    # False: tiene horas en el proyecto pero sin project.assignment vigente.
    assigned: bool = True
    # Vigencia del permiso `level` (inclusive); None = sin límite en ese extremo.
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


@dataclass
class LedProjectTeam:
    project: Project
    members: List[TeamMemberInfo]
    # Pendientes del mes actual (día 1 a hoy) y de fechas anteriores al día 1.
    pending_count: int = 0
    pending_previous_count: int = 0
    approver_names: List[str] = field(default_factory=list)
    # Si el actor ve este proyecto porque su líder le delegó la aprobación (y no
    # porque lo gerencie él): quién lo cubre y hasta cuándo (None = sin límite).
    covering_leader_id: Optional[int] = None
    covering_leader_name: Optional[str] = None
    covering_until: Optional[date] = None


@dataclass
class Coverage:
    """Delegación de aprobación vigente que recibió un empleado: actúa con la
    autoridad de ``leader_employee_id`` (su user de Odoo es ``leader_user_id``)."""

    leader_employee_id: int
    leader_user_id: int
    valid_until: Optional[date] = None


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
    # ------------------------------------------------------------------
    # Permisos delegados vigentes
    # ------------------------------------------------------------------
    def _active_permissions(
        self, member_employee_id: int
    ) -> List[TeamMemberPermission]:
        """Permisos que otros líderes le dieron a ``member_employee_id`` y que
        están vigentes HOY. Fuera de su ventana (``valid_from``/``valid_until``)
        un permiso no concede nada: así la cobertura de un líder de vacaciones
        vence sola."""
        today = date.today()
        return [
            p
            for p in self.permission_repo.list_by_member(member_employee_id)
            if p.is_active(today)
        ]

    # ------------------------------------------------------------------
    # Lecturas de autoridad con caché opcional (TTL corto, en memoria).
    # Solo para vistas de lectura: quien valida/borra llama sin ``cached`` y
    # consulta Odoo en el momento. No se guardan fallas ni ``None``.
    # ------------------------------------------------------------------
    def _user_id(self, employee_id: int, cached: bool = False) -> Optional[int]:
        if not cached:
            return self.employee_gateway.get_user_id_by_employee_id(employee_id)
        hit, value = _USER_ID_CACHE.get(employee_id)
        if hit:
            return value
        value = self.employee_gateway.get_user_id_by_employee_id(employee_id)
        # El gateway devuelve None también ante un error de Odoo: no se guarda.
        if value is not None:
            _USER_ID_CACHE.set(employee_id, value)
        return value

    def _led_projects(self, user_id: int, cached: bool = False) -> List[Project]:
        if not cached:
            return self.project_assignment_gateway.get_led_projects(user_id)
        hit, value = _LED_PROJECTS_CACHE.get(user_id)
        if hit:
            return value
        value = self.project_assignment_gateway.get_led_projects(user_id)
        _LED_PROJECTS_CACHE.set(user_id, value)
        return value

    def _approvers(
        self, project_ids: List[int], cached: bool = False
    ) -> Dict[int, List[Tuple[int, str]]]:
        ids = sorted(set(project_ids))
        if not cached:
            return self.project_assignment_gateway.get_project_approvers(ids)
        result: Dict[int, List[Tuple[int, str]]] = {}
        missing: List[int] = []
        for project_id in ids:
            hit, value = _APPROVERS_CACHE.get(project_id)
            if hit:
                result[project_id] = value
            else:
                missing.append(project_id)
        if missing:
            fetched = self.project_assignment_gateway.get_project_approvers(missing)
            for project_id, approvers in fetched.items():
                result[project_id] = approvers
                _APPROVERS_CACHE.set(project_id, approvers)
        return result

    def manages_project(
        self, leader_employee_id: int, project_id: int, cached: bool = False
    ) -> bool:
        """True si ``leader_employee_id`` es gerente o Project Manager de
        ``project_id`` en Odoo."""
        user_id = self._user_id(leader_employee_id, cached)
        if user_id is None:
            return False
        managed = self._led_projects(user_id, cached)
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
        for perm in self._active_permissions(member_employee_id):
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
    def _authorities(
        self, actor_employee_id: int, cached: bool = False
    ) -> List[Tuple[int, int]]:
        """Pares ``(employee_id, user_id)`` con cuya autoridad actúa el actor:
        él mismo y los líderes que le delegaron ``validate`` (mientras Odoo
        siga ubicándolo en el equipo de ese líder)."""
        authorities: List[Tuple[int, int]] = []
        own_user = self._user_id(actor_employee_id, cached)
        if own_user is not None:
            authorities.append((actor_employee_id, own_user))

        for cov in self._coverages(actor_employee_id, cached):
            authorities.append((cov.leader_employee_id, cov.leader_user_id))
        return authorities

    def _coverages(self, actor_employee_id: int, cached: bool = False) -> List[Coverage]:
        """Delegaciones ``validate`` VIGENTES hoy que recibió el actor, de líderes
        en cuyo equipo Odoo todavía lo ubica. La autoridad no se transmite: solo
        cuenta el líder que delegó directamente, no cadenas de delegación."""
        if cached:
            hit, value = _COVERAGE_CACHE.get(actor_employee_id)
            if hit:
                return value
        coverages: List[Coverage] = []
        for perm in self._active_permissions(actor_employee_id):
            if perm.level not in _VALIDATE_LEVELS:
                continue
            leader_id = perm.leader_employee_odoo_id
            if actor_employee_id not in {u["id"] for u in self.get_led_team(leader_id)}:
                continue
            leader_user = self._user_id(leader_id, cached)
            if leader_user is not None:
                coverages.append(Coverage(leader_id, leader_user, perm.valid_until))
        if cached:
            _COVERAGE_CACHE.set(actor_employee_id, coverages)
        return coverages

    def can_access_project(
        self, actor_employee_id: int, project_id: int, cached: bool = False
    ) -> bool:
        """True si el actor gerencia el proyecto o lo cubre porque su líder le
        delegó la aprobación (vigente hoy). Para ver su tablero; las acciones
        (validar/borrar) se siguen decidiendo por línea con ``lines_authority``."""
        if self.manages_project(actor_employee_id, project_id, cached):
            return True
        for cov in self._coverages(actor_employee_id, cached):
            if any(
                p.id == project_id for p in self._led_projects(cov.leader_user_id, cached)
            ):
                return True
        return False

    def lines_authority(
        self,
        actor_employee_id: int,
        lines: List[Tuple[int, int]],
        cached: bool = False,
    ) -> Dict[Tuple[int, int], bool]:
        """Para cada ``(employee_id, project_id)`` de una línea, si el actor
        puede validarla/borrarla.

        Regla: el Project Manager (``x_project_manager_id``) o el gerente
        (``project.project.user_id``) del proyecto: cualquiera de los dos.
        Si el proyecto no tiene ninguno, el jefe por jerarquía del empleado.
        Nunca sobre las propias horas ni (vía permiso delegado) sobre las del
        líder que delegó. Una sola lectura de aprobadores por llamada.

        ``cached=True`` es solo para mostrar permisos en vistas de lectura
        (puede estar desactualizado hasta el TTL). Para decidir si se ejecuta
        una acción (validar, borrar) NO usar: dejar ``cached=False``.
        """
        pairs = set(lines)
        if not pairs:
            return {}
        authorities = self._authorities(actor_employee_id, cached)
        if not authorities:
            return {pair: False for pair in pairs}

        approvers = self._approvers(
            [project_id for _, project_id in pairs], cached
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

    def project_approver_names(
        self, project_ids: List[int], cached: bool = False
    ) -> Dict[int, List[str]]:
        """Nombres de quienes pueden aprobar las horas de cada proyecto (PM y
        gerente), para mostrar quién debe aprobarlas."""
        approvers = self._approvers(project_ids, cached)
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
        for perm in self._active_permissions(employee_id):
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
        """Proyectos que gerencia ``leader_employee_id`` (y los de los líderes
        que le delegaron la aprobación, vigente hoy), con los empleados asignados
        a cada uno (excluyendo al propio líder y, en los proyectos que cubre, a
        quien le delegó: no se aprueban las horas de quien delegó).

        Los permisos locales de la vista plana (``get_led_team``/
        ``visible_team_members``) no cambian lo que se ve por proyecto: acá solo
        suma la cobertura, que da acceso a los proyectos de quien la otorgó.
        """
        timer = StepTimer("team.projects")
        # Vista de solo lectura: usa la caché de autoridad (TTL corto).
        user_id = timer.call("user_id", self._user_id, leader_employee_id, True)
        projects: List[Project] = []
        if user_id is not None:
            projects = list(
                timer.call("led_projects", self._led_projects, user_id, True)
            )

        # Proyectos de los líderes que le delegaron la aprobación.
        covered: Dict[int, Coverage] = {}
        own_ids = {p.id for p in projects}
        for cov in timer.call("coverages", self._coverages, leader_employee_id, True):
            for p in self._led_projects(cov.leader_user_id, True):
                if p.id not in own_ids and p.id not in covered:
                    covered[p.id] = cov
                    projects.append(p)

        if not projects:
            timer.log()
            return []

        def _excluded(project_id: int) -> Set[int]:
            cov = covered.get(project_id)
            return {leader_employee_id} | ({cov.leader_employee_id} if cov else set())

        project_ids = [p.id for p in projects]
        assignments = timer.call(
            "assignments",
            self.project_assignment_gateway.get_project_assignments,
            project_ids,
            date_from,
            date_to,
        )
        # Pendientes por PROYECTO (no por empleado): incluye las horas de quien
        # cargó sin estar (o antes de estar) asignado. Una sola consulta.
        pending_lines = timer.call(
            "pending_lines",
            self.timesheet_line_gateway.get_pending_lines_minimal,
            project_ids,
        )

        month_start = date.today().replace(day=1)
        pending_count_by_project: Dict[int, int] = defaultdict(int)
        pending_previous_by_project: Dict[int, int] = defaultdict(int)
        # project_id -> {employee_id: nombre} de quienes tienen pendientes
        with_pending: Dict[int, Dict[int, Optional[str]]] = defaultdict(dict)
        for line in pending_lines:
            employee = line.get("employee_id")
            project = line.get("project_id")
            if not employee or not project or employee[0] in _excluded(project[0]):
                continue
            project_id = project[0]
            with_pending[project_id][employee[0]] = (
                employee[1] if len(employee) > 1 else None
            )
            line_date = line.get("date")
            if line_date and date.fromisoformat(str(line_date)[:10]) < month_start:
                pending_previous_by_project[project_id] += 1
            else:
                pending_count_by_project[project_id] += 1

        assigned_by_project: Dict[int, Set[int]] = defaultdict(set)
        for a in assignments:
            employee = a.get("employee_id")
            project = a.get("project_id")
            if employee and project and employee[0] not in _excluded(project[0]):
                assigned_by_project[project[0]].add(employee[0])

        employee_ids = set().union(
            *assigned_by_project.values(),
            *(m.keys() for m in with_pending.values()),
            {c.leader_employee_id for c in covered.values()},
        )
        employees_by_id: Dict[int, Any] = {}
        if employee_ids:
            employees_by_id = {
                e.id: e
                for e in timer.call(
                    "employees", self.employee_gateway.get_by_ids, list(employee_ids)
                )
            }

        def _member(
            employee_id: int, fallback_name: Optional[str], assigned: bool
        ) -> TeamMemberInfo:
            emp = employees_by_id.get(employee_id)
            return TeamMemberInfo(
                employee_odoo_id=employee_id,
                name=emp.full_name if emp else fallback_name,
                email=emp.email if emp else None,
                level=None,
                assigned=assigned,
            )

        members_by_project: Dict[int, List[TeamMemberInfo]] = {}
        for pid in project_ids:
            assigned_ids = assigned_by_project.get(pid, set())
            members = [_member(eid, None, True) for eid in assigned_ids]
            # No asignados con horas pendientes (histórico previo a la asignación).
            members += [
                _member(eid, name, False)
                for eid, name in with_pending.get(pid, {}).items()
                if eid not in assigned_ids
            ]
            members_by_project[pid] = members

        approver_names = timer.call(
            "approver_names",
            self.project_approver_names,
            [p.id for p in projects],
            True,
        )
        timer.log()

        def _covering_name(project_id: int) -> Optional[str]:
            cov = covered.get(project_id)
            leader = employees_by_id.get(cov.leader_employee_id) if cov else None
            return leader.full_name if leader else None

        return [
            LedProjectTeam(
                project=p,
                approver_names=approver_names.get(p.id, []),
                members=members_by_project.get(p.id, []),
                pending_count=pending_count_by_project.get(p.id, 0),
                pending_previous_count=pending_previous_by_project.get(p.id, 0),
                covering_leader_id=(
                    covered[p.id].leader_employee_id if p.id in covered else None
                ),
                covering_leader_name=_covering_name(p.id),
                covering_until=(
                    covered[p.id].valid_until if p.id in covered else None
                ),
            )
            for p in projects
        ]
