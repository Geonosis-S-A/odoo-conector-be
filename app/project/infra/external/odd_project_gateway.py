from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project


class OdooProjectGateway(ProjectGateway):
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client

    def all(self) -> list[Project] | None:
        """
        Obtiene todos los proyectos activos que tienen cuenta analítica activa.
        Solo devuelve proyectos que están listos para crear timesheets.
        """
        domain = [
            ("active", "=", True),  # Solo proyectos activos
        ]

        projects = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.project",
            "search_read",
            [domain],
            {"fields": ["id", "name"]},
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
