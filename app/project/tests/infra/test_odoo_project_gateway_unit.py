from unittest.mock import Mock

from app.project.domain.models import Project
from app.project.infra.external.odd_project_gateway import OdooProjectGateway


def _odoo_client(execute_kw_side_effect):
    models = Mock()
    models.execute_kw.side_effect = execute_kw_side_effect
    return {
        "models": models,
        "uid": 1,
        "ODOO_DB": "db",
        "ODOO_PASSWORD": "pwd",
    }


class TestOdooProjectGatewayAllDomain:
    """Cobertura mockeada (sin Odoo real) del dominio de búsqueda de `all()`."""

    def test_domain_requires_active_stage_and_manager(self):
        captured = {}

        def side_effect(db, uid, pwd, model, method, args, kwargs):
            captured["domain"] = args[0]
            assert model == "project.project"
            assert method == "search_read"
            return [{"id": 1, "name": "Proyecto A", "stage_id": [1, "To Do"]}]

        gateway = OdooProjectGateway(_odoo_client(side_effect))
        projects = gateway.all()

        assert projects == [Project(id=1, name="Proyecto A")]
        assert ("active", "=", True) in captured["domain"]
        assert ("user_id", "!=", False) in captured["domain"]

    def test_all_returns_empty_list_when_odoo_returns_nothing(self):
        def side_effect(db, uid, pwd, model, method, args, kwargs):
            return []

        gateway = OdooProjectGateway(_odoo_client(side_effect))
        assert gateway.all() == []
