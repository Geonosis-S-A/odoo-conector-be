from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.infra.external.odoo.get_odoo import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_repository import (
    OdooTimesheetLineRepository,
)
from datetime import date
import pytest


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooRepository:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.odoo_client = get_odoo_connection()
        self.repository = OdooTimesheetLineRepository(self.odoo_client)
        yield
        # Limpieza después de cada test
        self._cleanup_test_data()

    def _cleanup_test_data(self):
        """Limpia los datos de prueba creados durante los tests"""
        test_lines = self.repository.all()
        for line in test_lines:
            if line.name == "Test Timesheet Line":
                if line.id:
                    self.repository.delete(line.id)

    def test_returns_all_timesheet_lines_is_more_than_one(self):
        # Act
        lines = self.repository.all()

        # Assert
        assert len(lines) > 0
        assert all(isinstance(line, TimesheetLine) for line in lines)
        assert all(hasattr(line, "employee_id") for line in lines)
        assert all(hasattr(line, "project_id") for line in lines)
        assert all(hasattr(line, "hours") for line in lines)
        assert all(hasattr(line, "date") for line in lines)

    def test_create_timesheet_line(self):
        # Arrange
        prev_lines = self.repository.all()
        test_date = date(2021, 1, 1)
        test_name = "Test Timesheet Line"

        timesheet_line = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date,
            name=test_name,
        )

        # Act
        created_id = self.repository.create(timesheet_line)
        post_lines = self.repository.all()

        # Assert
        assert len(post_lines) == len(prev_lines) + 1
        created_line = next(
            (line for line in post_lines if line.id == created_id), None
        )
        assert created_line is not None
        assert created_line.employee_id == 1
        assert created_line.project_id == 1
        assert created_line.hours == 1
        assert created_line.date == test_date
        assert created_line.name == test_name

    def test_delete_timesheet_line(self):
        # Arrange
        timesheet_line = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=date(2021, 1, 1),
            name="Test Timesheet Line",
        )
        created_id = self.repository.create(timesheet_line)
        prev_lines = self.repository.all()

        # Act
        delete_result = self.repository.delete(created_id)
        post_lines = self.repository.all()

        # Assert
        assert delete_result is True
        assert len(post_lines) == len(prev_lines) - 1
        assert not any(line.id == created_id for line in post_lines)
