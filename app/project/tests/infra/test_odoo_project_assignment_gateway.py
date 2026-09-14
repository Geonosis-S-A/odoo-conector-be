from datetime import date
from unittest.mock import Mock

import pytest

from app.project.domain.models import Project
from app.project.infra.external.odoo_project_assignment_gateway import (
    OdooProjectAssignmentGateway,
)


def _odoo_client(execute_kw_side_effect):
    models = Mock()
    models.execute_kw.side_effect = execute_kw_side_effect
    return {
        "models": models,
        "uid": 1,
        "ODOO_DB": "db",
        "ODOO_PASSWORD": "pwd",
    }


class TestOdooProjectAssignmentGateway:
    def test_get_managed_projects(self):
        def side_effect(db, uid, pwd, model, method, args, kwargs):
            assert model == "project.project"
            assert method == "search_read"
            assert args == [[("user_id", "=", 100)]]
            return [{"id": 1, "name": "Proyecto A"}]

        gateway = OdooProjectAssignmentGateway(_odoo_client(side_effect))
        projects = gateway.get_managed_projects(100)

        assert projects == [Project(id=1, name="Proyecto A", manager_user_id=100)]

    def test_get_team_users_no_managed_projects_returns_empty(self):
        def side_effect(db, uid, pwd, model, method, args, kwargs):
            if model == "project.project" and method == "search":
                return []
            raise AssertionError("no debería llamarse a nada más")

        gateway = OdooProjectAssignmentGateway(_odoo_client(side_effect))
        assert gateway.get_team_users(user_id=100, employee_id=1) == []

    def test_get_team_users_excludes_requester_and_deduplicates(self):
        calls = []

        def side_effect(db, uid, pwd, model, method, args, kwargs):
            calls.append((model, method, args, kwargs))
            if model == "project.project" and method == "search":
                return [1, 2]
            if model == "project.assignment" and method == "search_read":
                return [
                    {"employee_id": [10, "Ana"], "project_id": [1, "P1"]},
                    {"employee_id": [20, "Beto"], "project_id": [2, "P2"]},
                    {"employee_id": [5, "Yo"], "project_id": [1, "P1"]},
                ]
            if model == "hr.employee" and method == "search_read":
                ids = args[0][0][2]
                assert set(ids) == {10, 20}
                return [
                    {"id": 10, "name": "Ana", "work_email": "ana@x.com"},
                    {"id": 20, "name": "Beto", "work_email": "beto@x.com"},
                ]
            raise AssertionError(f"llamada inesperada: {model}.{method}")

        gateway = OdooProjectAssignmentGateway(_odoo_client(side_effect))
        team = gateway.get_team_users(user_id=100, employee_id=5)

        assert {u["id"] for u in team} == {10, 20}

    def test_get_project_assignments_filters_by_validity_range(self):
        def side_effect(db, uid, pwd, model, method, args, kwargs):
            assert model == "project.assignment"
            assert method == "search_read"
            domain = args[0]
            assert ("project_id", "in", [1]) in domain
            assert ("date_start", "<=", "2024-01-31") in domain
            assert ("date_end", "=", False) in domain
            assert ("date_end", ">=", "2024-01-01") in domain
            return [{"employee_id": [10, "Ana"], "project_id": [1, "P1"]}]

        gateway = OdooProjectAssignmentGateway(_odoo_client(side_effect))
        rows = gateway.get_project_assignments(
            [1], date_from=date(2024, 1, 1), date_to=date(2024, 1, 31)
        )
        assert len(rows) == 1

    def test_get_project_assignments_empty_project_ids_short_circuits(self):
        gateway = OdooProjectAssignmentGateway(_odoo_client(lambda *a, **k: []))
        assert gateway.get_project_assignments([]) == []

    def test_get_employee_assigned_projects(self):
        def side_effect(db, uid, pwd, model, method, args, kwargs):
            if model == "project.assignment":
                return [{"project_id": [1, "P1"]}, {"project_id": [2, "P2"]}]
            if model == "project.project":
                assert ("id", "in", [1, 2]) in args[0] or set(
                    args[0][0][2]
                ) == {1, 2}
                return [{"id": 1, "name": "P1"}, {"id": 2, "name": "P2"}]
            raise AssertionError

        gateway = OdooProjectAssignmentGateway(_odoo_client(side_effect))
        projects = gateway.get_employee_assigned_projects(7)
        assert {p.id for p in projects} == {1, 2}

    def test_get_employee_assigned_projects_no_assignments_returns_empty(self):
        def side_effect(db, uid, pwd, model, method, args, kwargs):
            if model == "project.assignment":
                return []
            raise AssertionError("no debería consultar project.project sin asignaciones")

        gateway = OdooProjectAssignmentGateway(_odoo_client(side_effect))
        assert gateway.get_employee_assigned_projects(7) == []

    @pytest.mark.parametrize("count,expected", [(1, True), (0, False)])
    def test_is_employee_assigned(self, count, expected):
        def side_effect(db, uid, pwd, model, method, args, kwargs):
            assert model == "project.assignment"
            assert method == "search_count"
            return count

        gateway = OdooProjectAssignmentGateway(_odoo_client(side_effect))
        assert (
            gateway.is_employee_assigned(7, 1, at_date=date(2024, 1, 15)) is expected
        )
