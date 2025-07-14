from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
import pytest
from app.users.domain.models import Employee
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooEmployeeGateway:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.odoo_client = get_odoo_connection()
        self.repository = OdooEmployeeGateway(self.odoo_client)

    def test_returns_all_employees_is_more_than_one(self):
        # Act
        employees = self.repository.all()
        # Assert
        assert len(employees) > 0
        assert all(isinstance(employee, Employee) for employee in employees)
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

    def test_employee_required_fields_not_empty(self):
        # Act
        employees = self.repository.all()

        # Assert
        for employee in employees:
            assert employee.id is not None
            assert employee.email != ""
            assert employee.full_name != ""
