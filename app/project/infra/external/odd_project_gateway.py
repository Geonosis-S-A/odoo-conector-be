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
        # Filtrar solo proyectos activos que tengan cuenta analítica
        domain = [
            ("active", "=", True),  # Solo proyectos activos
            ("analytic_account_id", "!=", False),  # Solo proyectos con cuenta analítica
        ]

        projects = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.project",
            "search_read",
            [domain],
            {"fields": ["id", "name", "analytic_account_id"]},
        )

        if not projects:
            return []

        # Obtener IDs de cuentas analíticas para verificar su estado
        analytic_account_ids = []
        for project in projects:
            analytic_account = project.get("analytic_account_id")
            if (
                analytic_account
                and isinstance(analytic_account, list)
                and len(analytic_account) > 0
            ):
                analytic_account_ids.append(analytic_account[0])

        # Verificar qué cuentas analíticas están activas
        active_analytic_accounts = set()
        if analytic_account_ids:
            analytic_accounts = self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.account",
                "search_read",
                [
                    [
                        ("id", "in", analytic_account_ids),
                        ("active", "=", True),  # Solo cuentas analíticas activas
                    ]
                ],
                {"fields": ["id"]},
            )

            active_analytic_accounts = {acc["id"] for acc in analytic_accounts}

        # Filtrar proyectos que tienen cuenta analítica activa
        valid_projects = []
        for project in projects:
            analytic_account = project.get("analytic_account_id")
            if (
                analytic_account
                and isinstance(analytic_account, list)
                and len(analytic_account) > 0
                and analytic_account[0] in active_analytic_accounts
            ):
                valid_projects.append(Project(id=project["id"], name=project["name"]))

        return valid_projects
