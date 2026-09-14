from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, Optional

from app.project.domain.models import Project

# Se definen las interfaces de los repositorios


class ProjectGateway(ABC):
    @abstractmethod
    def all(self) -> list[Project] | None:
        pass


class ProjectAssignmentGateway(ABC):
    """Resuelve equipos y proyectos a partir de `project.assignment` (asignación
    empleado<->proyecto en Odoo), reemplazando el criterio de jerarquía RRHH.

    Los métodos con `date_from`/`date_to` evalúan vigencia por solapamiento con
    ese rango; si se omiten, ambos valores caen en la fecha actual.
    """

    @abstractmethod
    def get_team_users(
        self,
        user_id: int,
        employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Dict[str, Any]]:
        """Empleados asignados a proyectos gerenciados por `user_id`, excluyendo `employee_id`.

        Mismo shape que el `get_team_users` legado: `{"id","name","work_email"}`.
        """

    @abstractmethod
    def get_managed_projects(self, user_id: int) -> list[Project]:
        """Proyectos donde `project.project.user_id == user_id` (Project Manager)."""

    @abstractmethod
    def get_project_assignments(
        self,
        project_ids: list[int],
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Dict[str, Any]]:
        """Asignaciones vigentes de esos proyectos en el rango dado (filas crudas)."""

    @abstractmethod
    def get_employee_assigned_projects(
        self,
        employee_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Project]:
        """Proyectos activos a los que `employee_id` está asignado en el rango dado."""

    @abstractmethod
    def is_employee_assigned(
        self, employee_id: int, project_id: int, at_date: date
    ) -> bool:
        """True si `employee_id` tiene una asignación vigente a `project_id` en `at_date`."""
