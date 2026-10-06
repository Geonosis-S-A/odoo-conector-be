from typing import Optional

from app.project.domain.gateway import ProjectAssignmentGateway
from app.project.domain.models import Project


class ObtenerProyectosAsignadosUseCase:
    """Proyectos que un empleado puede ver para cargar horas: a los que está
    asignado (``project.assignment`` vigente) más los que gerencia."""

    def __init__(self, project_assignment_gateway: ProjectAssignmentGateway):
        self.project_assignment_gateway = project_assignment_gateway

    def execute(self, employee_id: int, user_id: Optional[int] = None) -> list[Project]:
        assigned = self.project_assignment_gateway.get_employee_assigned_projects(
            employee_id
        )
        managed = (
            self.project_assignment_gateway.get_managed_projects(user_id)
            if user_id
            else []
        )
        return list({p.id: p for p in assigned + managed}.values())
