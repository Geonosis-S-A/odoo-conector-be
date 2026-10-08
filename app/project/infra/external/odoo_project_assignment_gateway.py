from datetime import date
from typing import Any, Dict, List, Optional, Set

from app.project.domain.gateway import ProjectAssignmentGateway
from app.project.domain.models import Project
from app.shared.security.project_stages import ProjectStages


class OdooProjectAssignmentGateway(ProjectAssignmentGateway):
    """Equipos y proyectos derivados de `project.assignment` (Odoo).

    `project.project.user_id` es el gerente del proyecto (líder). La vigencia de
    una asignación se evalúa sólo contra `date_start` (¿ya arrancó, relativo al
    rango [date_from, date_to] consultado?). `date_end` NO se usa como corte: es
    una fecha *estimada* que en la práctica se extiende sin que nadie la
    actualice en Odoo a tiempo, y tratarla como corte duro sacaba gente del
    equipo (y le bloqueaba cargar horas) apenas se cumplía la estimación.
    """

    def __init__(self, odoo_client):
        self.odoo_client = odoo_client

    def _execute_kw(self, model: str, method: str, args: list, kwargs: Optional[dict] = None):
        return self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            model,
            method,
            args,
            kwargs or {},
        )

    @staticmethod
    def _validity_domain(date_from: date, date_to: date) -> list:
        # Sólo exige que la asignación ya haya arrancado. `date_end` es una
        # fecha estimada, no un corte real de vigencia (ver docstring).
        return [("date_start", "<=", date_to.isoformat())]

    @staticmethod
    def _resolve_range(
        date_from: Optional[date], date_to: Optional[date]
    ) -> tuple[date, date]:
        today = date.today()
        return (date_from or today, date_to or today)

    @staticmethod
    def _managed_projects_domain(user_id: int) -> list:
        # Sólo proyectos vigentes (To Do / In Progress): los "Done"/cancelados
        # ya finalizaron y no deben aportar equipo ni impactar la carga de horas.
        return [
            ("user_id", "=", user_id),
            ("active", "=", True),
            ("stage_id", "not in", ProjectStages.inactive_stages()),
        ]

    @staticmethod
    def _led_projects_domain(user_id: int) -> list:
        # Vigentes donde es gerente o Project Manager.
        return [
            ("active", "=", True),
            ("stage_id", "not in", ProjectStages.inactive_stages()),
            "|",
            ("user_id", "=", user_id),
            ("x_project_manager_id", "=", user_id),
        ]

    def _managed_project_ids(self, user_id: int, only_active: bool = False) -> List[int]:
        # Por defecto sin filtrar por etapa y sólo por gerente (comportamiento
        # histórico, lo que usan los reportes); con only_active, los proyectos
        # vigentes donde es gerente o PM.
        domain = (
            self._led_projects_domain(user_id)
            if only_active
            else [("user_id", "=", user_id)]
        )
        return self._execute_kw("project.project", "search", [domain])

    def get_led_projects(self, user_id: int) -> list[Project]:
        rows = self._execute_kw(
            "project.project",
            "search_read",
            [self._led_projects_domain(user_id)],
            {"fields": ["id", "name"], "context": {"lang": "es_AR"}},
        )
        return [
            Project(id=r["id"], name=r["name"], manager_user_id=user_id) for r in rows
        ]

    def get_project_approvers(
        self, project_ids: list[int]
    ) -> Dict[int, list[tuple[int, str]]]:
        if not project_ids:
            return {}
        rows = self._execute_kw(
            "project.project",
            "search_read",
            [[("id", "in", project_ids)]],
            # active_test False: un proyecto archivado/finalizado conserva
            # aprobadores y sus horas pendientes siguen siendo aprobables.
            {
                "fields": ["id", "user_id", "x_project_manager_id"],
                "context": {"active_test": False},
            },
        )
        result: Dict[int, list[tuple[int, str]]] = {}
        for r in rows:
            approvers: list[tuple[int, str]] = []
            for field in ("x_project_manager_id", "user_id"):
                value = r.get(field)
                if value and all(value[0] != a[0] for a in approvers):
                    approvers.append((value[0], value[1]))
            result[r["id"]] = approvers
        return result

    def is_project_manager_only(self, user_id: int) -> bool:
        vigentes = [
            ("active", "=", True),
            ("stage_id", "not in", ProjectStages.inactive_stages()),
        ]
        is_pm = self._execute_kw(
            "project.project",
            "search_count",
            [vigentes + [("x_project_manager_id", "=", user_id)]],
        )
        if not is_pm:
            return False
        is_manager = self._execute_kw(
            "project.project", "search_count", [vigentes + [("user_id", "=", user_id)]]
        )
        return not is_manager

    def _employee_ids_with_lines(self, project_ids: List[int]) -> Set[int]:
        groups = self._execute_kw(
            "account.analytic.line",
            "read_group",
            [
                [("is_timesheet", "=", True), ("project_id", "in", project_ids)],
                ["employee_id"],
                ["employee_id"],
            ],
            {"lazy": False},
        )
        return {g["employee_id"][0] for g in groups if g.get("employee_id")}

    def get_managed_projects(self, user_id: int) -> list[Project]:
        rows = self._execute_kw(
            "project.project",
            "search_read",
            [self._managed_projects_domain(user_id)],
            {"fields": ["id", "name"], "context": {"lang": "es_AR"}},
        )
        return [
            Project(id=r["id"], name=r["name"], manager_user_id=user_id) for r in rows
        ]

    def get_project_manager_user_ids(
        self, project_ids: list[int]
    ) -> Dict[int, Optional[int]]:
        if not project_ids:
            return {}
        rows = self._execute_kw(
            "project.project",
            "search_read",
            [[("id", "in", project_ids)]],
            # active_test False: un proyecto archivado/finalizado conserva
            # gerente y sus horas pendientes siguen siendo aprobables.
            {"fields": ["id", "user_id"], "context": {"active_test": False}},
        )
        return {
            r["id"]: (r["user_id"][0] if r.get("user_id") else None) for r in rows
        }

    def get_project_assignments(
        self,
        project_ids: list[int],
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Dict[str, Any]]:
        if not project_ids:
            return []
        resolved_from, resolved_to = self._resolve_range(date_from, date_to)
        domain = [
            "&",
            ("project_id", "in", project_ids),
        ] + self._validity_domain(resolved_from, resolved_to)
        return self._execute_kw(
            "project.assignment",
            "search_read",
            [domain],
            {
                "fields": [
                    "employee_id",
                    "project_id",
                    "date_start",
                    "date_end",
                    "allocation_percentage",
                ]
            },
        )

    def get_team_users(
        self,
        user_id: int,
        employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        only_active: bool = False,
    ) -> list[Dict[str, Any]]:
        project_ids = self._managed_project_ids(user_id, only_active)
        if not project_ids:
            return []

        assignments = self.get_project_assignments(project_ids, date_from, date_to)
        employee_ids = {
            a["employee_id"][0] for a in assignments if a.get("employee_id")
        }
        if only_active:
            # Además de los asignados, quienes cargaron horas en el proyecto
            # sin tener (o ya sin) asignación vigente.
            employee_ids |= self._employee_ids_with_lines(project_ids)
        employee_ids.discard(employee_id)
        if not employee_ids:
            return []

        return self._execute_kw(
            "hr.employee",
            "search_read",
            [[("id", "in", list(employee_ids))]],
            {"fields": ["id", "name", "work_email"]},
        )

    def get_employee_assigned_projects(
        self,
        employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Project]:
        resolved_from, resolved_to = self._resolve_range(date_from, date_to)
        domain = [
            "&",
            ("employee_id", "=", employee_id),
        ] + self._validity_domain(resolved_from, resolved_to)
        assignments = self._execute_kw(
            "project.assignment", "search_read", [domain], {"fields": ["project_id"]}
        )
        project_ids = list(
            {a["project_id"][0] for a in assignments if a.get("project_id")}
        )
        if not project_ids:
            return []

        domain_projects = [
            ("id", "in", project_ids),
            ("active", "=", True),
            ("stage_id", "not in", ProjectStages.inactive_stages()),
        ]
        rows = self._execute_kw(
            "project.project",
            "search_read",
            [domain_projects],
            {"fields": ["id", "name"], "context": {"lang": "es_AR"}},
        )
        return [Project(id=r["id"], name=r["name"]) for r in rows]

    def is_employee_assigned(
        self, employee_id: int, project_id: int, at_date: date
    ) -> bool:
        domain = [
            "&",
            "&",
            ("employee_id", "=", employee_id),
            ("project_id", "=", project_id),
        ] + self._validity_domain(at_date, at_date)
        count = self._execute_kw("project.assignment", "search_count", [domain])
        return bool(count)

    def get_assignment_start_date(
        self, employee_id: int, project_id: int
    ) -> Optional[date]:
        rows = self._execute_kw(
            "project.assignment",
            "search_read",
            [[("employee_id", "=", employee_id), ("project_id", "=", project_id)]],
            {"fields": ["date_start"], "order": "date_start asc", "limit": 1},
        )
        if not rows or not rows[0].get("date_start"):
            return None
        return date.fromisoformat(str(rows[0]["date_start"])[:10])

    def get_project_name(self, project_id: int) -> Optional[str]:
        rows = self._execute_kw(
            "project.project",
            "search_read",
            [[("id", "=", project_id)]],
            {
                "fields": ["name"],
                "limit": 1,
                "context": {"active_test": False, "lang": "es_AR"},
            },
        )
        return rows[0]["name"] if rows else None
