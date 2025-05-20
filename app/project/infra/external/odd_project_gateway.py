from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project


class OdooProjectGateway(ProjectGateway):
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client

    def all(self, user_id: int | None = None) -> list[Project]:
        domain = []
        if user_id is not None:
            domain = [("user_id", "=", user_id)]

        projects = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.project",
            "search_read",
            [domain],
            {"fields": ["id", "name"]},
        )
        print(projects)
        return [Project(id=project["id"], name=project["name"]) for project in projects]
