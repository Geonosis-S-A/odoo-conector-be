from app.timesheet_line.domain.models import TimesheetLine
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from datetime import date
import pytest
from app.users.domain.models import User
from app.users.infra.external.odoo_repository import OdooEmployeeRepository


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooUserRepository:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.odoo_client = get_odoo_connection()
        self.repository = OdooEmployeeRepository(self.odoo_client)

    def test_returns_all_employees_is_more_than_one(self):
        # Act
        employees = self.repository.all()

        # Assert
        assert len(employees) > 0
        assert all(isinstance(employee, User) for employee in employees)
        assert all(hasattr(employee, "id") for employee in employees)
        assert all(hasattr(employee, "email") for employee in employees)
        assert all(hasattr(employee, "full_name") for employee in employees)

    def test_employee_data_structure(self):
        # Act
        employees = self.repository.all()
        first_employee = employees[0]

        # Assert
        assert isinstance(first_employee.id, int)
        assert isinstance(first_employee.email, str)
        assert isinstance(first_employee.full_name, str)
        assert isinstance(first_employee.is_active, bool)
        assert isinstance(first_employee.is_superuser, bool)

    def test_employee_required_fields_not_empty(self):
        # Act
        employees = self.repository.all()

        # Assert
        for employee in employees:
            assert employee.id is not None
            assert employee.email != ""
            assert employee.full_name != ""
