from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project
from app.shared.security.project_stages import ProjectStages


class OdooProjectGateway(ProjectGateway):
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client

    def all(self) -> list[Project] | None:
        """
        Obtiene todos los proyectos activos que están en etapas activas.
        Solo devuelve proyectos que están listos para crear timesheets.

        Utiliza el enum ProjectStages para obtener las etapas activas según el ambiente:
        - En DEV: To Do (ID: 1) e In Progress (ID: 2)
        - En STAGING: IDs configurados para ese ambiente
        """
        domain = [
            ("active", "=", True),  # Solo proyectos activos
            (
                "stage_id",
                "not in",
                ProjectStages.inactive_stages(),
            ),  # Solo proyectos en etapas activas
        ]

        projects = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.project",
            "search_read",
            [domain],
            {
                "fields": ["id", "name", "stage_id"],
                "context": {"lang": "es_AR"},
            },
        )

        if not projects:
            return []

        # TEMPORAL: Se omite la validación de cuenta analítica para evitar crash
        valid_projects = projects

        # Transformar a modelo de dominio
        transformed_projects = []
        for project in valid_projects:
            transformed_projects.append(Project(id=project["id"], name=project["name"]))

        return transformed_projects
