from datetime import date
import pytest
from unittest.mock import Mock

from app.project.domain.gateway import ProjectAssignmentGateway
from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    DailyHoursLimitExceededError,
    EmployeeNotAssignedToProjectError,
    InvalidHoursError,
    TimesheetCreationError,
)
from app.users.domain.repositories import EmployeeGateway


class TestCargarHorasUseCase:
    @pytest.fixture
    def mock_gateway(self):
        gw = Mock(spec=TimesheetLineGateway)
        gw.all.return_value = []  # sin horas previas en el día
        return gw

    @pytest.fixture
    def mock_project_assignment_gateway(self):
        gw = Mock(spec=ProjectAssignmentGateway)
        gw.is_employee_assigned.return_value = True
        gw.get_project_name.return_value = "CARGA MASIVA"
        gw.get_assignment_start_date.return_value = None
        return gw

    @pytest.fixture
    def use_case(self, mock_gateway, mock_project_assignment_gateway):
        return CargarHorasUseCase(mock_gateway, mock_project_assignment_gateway)

    def test_execute_creates_timesheet_line_without_task(self, use_case, mock_gateway):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
            )
        ]
        mock_gateway.create.return_value = [123]
        mock_gateway.get_by_ids.return_value = [Mock()]

        # Act
        result = use_case.execute(requests)

        # Assert
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_ids.assert_called_once_with([123])
        created_timesheet_lines = mock_gateway.create.call_args[0][0]
        assert len(created_timesheet_lines) == 1
        created_timesheet = created_timesheet_lines[0]
        assert created_timesheet.name == requests[0].name
        assert created_timesheet.employee_id == requests[0].employee_id
        assert created_timesheet.project_id == requests[0].project_id
        assert created_timesheet.hours == requests[0].hours
        assert created_timesheet.date == requests[0].date
        assert created_timesheet.id is None
        assert created_timesheet.task_id is None
        assert isinstance(result, list)
        assert len(result) == 1

    def test_execute_creates_timesheet_line_with_task(self, use_case, mock_gateway):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
                task_id=123,
            )
        ]
        mock_gateway.create.return_value = [456]
        mock_gateway.get_by_ids.return_value = [Mock()]

        # Act
        result = use_case.execute(requests)

        # Assert
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_ids.assert_called_once_with([456])
        created_timesheet_lines = mock_gateway.create.call_args[0][0]
        assert len(created_timesheet_lines) == 1
        created_timesheet = created_timesheet_lines[0]
        assert created_timesheet.name == requests[0].name
        assert created_timesheet.employee_id == requests[0].employee_id
        assert created_timesheet.project_id == requests[0].project_id
        assert created_timesheet.hours == requests[0].hours
        assert created_timesheet.date == requests[0].date
        assert created_timesheet.id is None
        assert created_timesheet.task_id == 123
        assert isinstance(result, list)
        assert len(result) == 1

    def test_execute_raises_invalid_hours_error_for_negative_hours(self, use_case):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=-1.0,  # Horas negativas
                date=date(2024, 1, 1),
            )
        ]

        # Act & Assert
        with pytest.raises(InvalidHoursError) as exc_info:
            use_case.execute(requests)

        assert "Las horas no pueden ser negativas" in str(exc_info.value.message)
        assert "-1.0" in str(exc_info.value.message)

    def _request(self, project_id: int = 99) -> CargarHorasRequest:
        return CargarHorasRequest(
            name="Test Task",
            employee_id=1,
            project_id=project_id,
            hours=8.0,
            date=date(2024, 1, 1),
        )

    def test_error_message_explains_date_before_assignment_start(
        self, use_case, mock_project_assignment_gateway
    ):
        from datetime import date as _date

        mock_project_assignment_gateway.is_employee_assigned.return_value = False
        mock_project_assignment_gateway.get_assignment_start_date.return_value = (
            _date(2026, 10, 5)
        )
        req = CargarHorasRequest(
            name="x", employee_id=1, project_id=153, hours=8.0, date=_date(2026, 10, 1)
        )

        with pytest.raises(EmployeeNotAssignedToProjectError) as exc:
            use_case.execute([req])

        assert exc.value.message == (
            "No podés cargar horas al proyecto «CARGA MASIVA» con fecha "
            "01/10/2026: tu asignación comienza el 05/10/2026."
        )

    def test_error_message_when_never_assigned(
        self, use_case, mock_project_assignment_gateway
    ):
        mock_project_assignment_gateway.is_employee_assigned.return_value = False

        with pytest.raises(EmployeeNotAssignedToProjectError) as exc:
            use_case.execute([self._request()])

        assert "No tenés una asignación vigente al proyecto «CARGA MASIVA»" in (
            exc.value.message
        )

    def test_execute_rejects_project_without_assignment(
        self, use_case, mock_gateway, mock_project_assignment_gateway
    ):
        mock_project_assignment_gateway.is_employee_assigned.return_value = False

        with pytest.raises(EmployeeNotAssignedToProjectError):
            use_case.execute([self._request()])

        mock_project_assignment_gateway.is_employee_assigned.assert_called_once_with(
            1, 99, date(2024, 1, 1)
        )
        mock_gateway.create.assert_not_called()

    def test_execute_allows_project_manager_without_assignment(
        self, mock_gateway, mock_project_assignment_gateway
    ):
        mock_project_assignment_gateway.is_employee_assigned.return_value = False
        mock_project_assignment_gateway.get_project_approvers.return_value = {
            99: [(100, "Gerente")]
        }
        employee_gateway = Mock(spec=EmployeeGateway)
        employee_gateway.get_user_id_by_employee_id.return_value = 100
        mock_gateway.create.return_value = [123]
        mock_gateway.get_by_ids.return_value = [Mock()]
        use_case = CargarHorasUseCase(
            mock_gateway, mock_project_assignment_gateway, employee_gateway
        )

        result = use_case.execute([self._request()])

        assert len(result) == 1

    def test_execute_allows_project_manager_field_without_assignment(
        self, mock_gateway, mock_project_assignment_gateway
    ):
        # El PM (x_project_manager_id) viene como segundo aprobador del proyecto.
        mock_project_assignment_gateway.is_employee_assigned.return_value = False
        mock_project_assignment_gateway.get_project_approvers.return_value = {
            99: [(200, "Gerente"), (100, "PM")]
        }
        employee_gateway = Mock(spec=EmployeeGateway)
        employee_gateway.get_user_id_by_employee_id.return_value = 100
        mock_gateway.create.return_value = [123]
        mock_gateway.get_by_ids.return_value = [Mock()]
        use_case = CargarHorasUseCase(
            mock_gateway, mock_project_assignment_gateway, employee_gateway
        )

        assert len(use_case.execute([self._request()])) == 1

    def test_execute_rejects_when_other_user_manages_project(
        self, mock_gateway, mock_project_assignment_gateway
    ):
        mock_project_assignment_gateway.is_employee_assigned.return_value = False
        mock_project_assignment_gateway.get_project_approvers.return_value = {
            99: [(200, "Otro")]
        }
        employee_gateway = Mock(spec=EmployeeGateway)
        employee_gateway.get_user_id_by_employee_id.return_value = 100
        use_case = CargarHorasUseCase(
            mock_gateway, mock_project_assignment_gateway, employee_gateway
        )

        with pytest.raises(EmployeeNotAssignedToProjectError):
            use_case.execute([self._request()])

    def test_execute_validates_whole_batch_before_creating(
        self, use_case, mock_gateway, mock_project_assignment_gateway
    ):
        # La primera línea es válida, la segunda no: no se crea ninguna.
        mock_project_assignment_gateway.is_employee_assigned.side_effect = [True, False]

        with pytest.raises(EmployeeNotAssignedToProjectError):
            use_case.execute([self._request(1), self._request(2)])

        mock_gateway.create.assert_not_called()

    def test_execute_raises_timesheet_creation_error_when_create_fails(
        self, use_case, mock_gateway
    ):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
            )
        ]
        mock_gateway.create.return_value = None  # Simula fallo en creación

        # Act & Assert
        with pytest.raises(TimesheetCreationError):
            use_case.execute(requests)

    def test_execute_raises_timesheet_not_found_error_when_get_by_ids_fails(
        self, use_case, mock_gateway
    ):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
            )
        ]
        mock_gateway.create.return_value = [123]
        mock_gateway.get_by_ids.return_value = []  # Simula que no se encuentran las líneas creadas

        # Act & Assert
        with pytest.raises(TimesheetCreationError) as exc_info:
            use_case.execute(requests)

        assert "No se pudieron obtener las líneas de timesheet creadas" in str(
            exc_info.value.message
        )

    def test_execute_partial_success_returns_only_successful_timesheets(
        self, use_case, mock_gateway
    ):
        # Arrange - Crear múltiples requests
        requests = [
            CargarHorasRequest(
                name="Test Task 1",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
            ),
            CargarHorasRequest(
                name="Test Task 2",
                employee_id=1,
                project_id=1,
                hours=4.0,
                date=date(2024, 1, 2),
            ),
            CargarHorasRequest(
                name="Test Task 3",
                employee_id=1,
                project_id=1,
                hours=6.0,
                date=date(2024, 1, 3),
            ),
        ]

        # Mock: create devuelve solo 2 IDs (el tercero falló)
        mock_gateway.create.return_value = [123, 456]  # Solo 2 de 3 se crearon

        # Mock: get_by_ids devuelve solo los timesheets que se crearon exitosamente
        mock_successful_timesheet_1 = Mock()
        mock_successful_timesheet_1.id = 123
        mock_successful_timesheet_1.name = "Test Task 1"

        mock_successful_timesheet_2 = Mock()
        mock_successful_timesheet_2.id = 456
        mock_successful_timesheet_2.name = "Test Task 2"

        mock_gateway.get_by_ids.return_value = [
            mock_successful_timesheet_1,
            mock_successful_timesheet_2,
        ]

        # Act
        result = use_case.execute(requests)

        # Assert
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_ids.assert_called_once_with([123, 456])

        # Verificar que se enviaron 3 timesheets para crear
        created_timesheet_lines = mock_gateway.create.call_args[0][0]
        assert len(created_timesheet_lines) == 3

        # Verificar que solo se devolvieron los 2 exitosos
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].id == 123
        assert result[1].id == 456
        assert result[0].name == "Test Task 1"
        assert result[1].name == "Test Task 2"


class TestTopeDeHorasPorDia:
    """Nadie puede tener más de 24 h cargadas en un mismo día."""

    DAY = date(2024, 1, 10)

    def _use_case(self, existing_hours=()):
        gw = Mock(spec=TimesheetLineGateway)
        gw.all.return_value = [Mock(hours=h) for h in existing_hours]
        gw.create.return_value = [1]
        gw.get_by_ids.return_value = [Mock()]
        assignment = Mock(spec=ProjectAssignmentGateway)
        assignment.is_employee_assigned.return_value = True
        return CargarHorasUseCase(gw, assignment), gw

    def _req(self, hours, day=None, project_id=1, employee_id=1):
        return CargarHorasRequest(
            name=None,
            employee_id=employee_id,
            project_id=project_id,
            hours=hours,
            date=day or self.DAY,
        )

    def test_24_horas_en_un_dia_vacio_se_permiten(self):
        use_case, gw = self._use_case()
        use_case.execute([self._req(24)])
        gw.create.assert_called_once()

    def test_mas_de_24_en_una_sola_linea_se_rechaza(self):
        use_case, gw = self._use_case()
        with pytest.raises(DailyHoursLimitExceededError):
            use_case.execute([self._req(24.5)])
        gw.create.assert_not_called()

    def test_se_cuentan_las_horas_ya_cargadas_en_otros_proyectos(self):
        use_case, gw = self._use_case(existing_hours=[8, 8])
        with pytest.raises(DailyHoursLimitExceededError) as exc:
            use_case.execute([self._req(9)])
        assert exc.value.existing == 16
        assert "24" in exc.value.message
        gw.create.assert_not_called()

    def test_justo_en_el_tope_con_horas_previas_se_permite(self):
        use_case, gw = self._use_case(existing_hours=[8, 8])
        use_case.execute([self._req(8)])
        gw.create.assert_called_once()

    def test_el_lote_suma_las_lineas_del_mismo_dia(self):
        use_case, gw = self._use_case()
        with pytest.raises(DailyHoursLimitExceededError):
            use_case.execute([self._req(12, project_id=1), self._req(13, project_id=2)])
        gw.create.assert_not_called()

    def test_el_lote_en_dias_distintos_no_se_suma(self):
        use_case, gw = self._use_case()
        use_case.execute([self._req(20), self._req(20, day=date(2024, 1, 11))])
        gw.create.assert_called_once()
