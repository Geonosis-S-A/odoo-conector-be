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

        Cruza empresas sin problema (un proyecto de otra compañía es válido
        para cargar horas). Lo que se descarta son proyectos sin
        ``user_id`` (gerente de proyecto): en la práctica son registros
        huérfanos/incompletos en Odoo (sin cliente real, sin cuenta
        analítica configurada), no proyectos donde alguien pueda trabajar.
        """
        domain = [
            ("active", "=", True),  # Solo proyectos activos
            (
                "stage_id",
                "not in",
                ProjectStages.inactive_stages(),
            ),  # Solo proyectos en etapas activas
            ("user_id", "!=", False),  # Solo proyectos con gerente asignado
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

        return [
            Project(id=project["id"], name=project["name"]) for project in projects
        ]
