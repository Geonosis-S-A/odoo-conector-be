import pytest
from unittest.mock import Mock
from datetime import date

from app.employee_price.application.use_cases.list_team_employee_prices import (
    ListTeamEmployeePricesUseCase,
)
from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway
from app.users.domain.models import Employee


class TestListTeamEmployeePricesUseCase:
    @pytest.fixture
    def mock_employee_price_repository(self):
        """Fixture que proporciona un repositorio de precios mockeado."""
        return Mock(spec=EmployeePriceRepository)

    @pytest.fixture
    def mock_timesheet_gateway(self):
        """Fixture que proporciona un gateway de timesheet mockeado."""
        return Mock(spec=TimesheetLineGateway)

    @pytest.fixture
    def mock_employee_gateway(self):
        """Fixture que proporciona un gateway de empleados mockeado."""
        return Mock(spec=EmployeeGateway)

    @pytest.fixture
    def use_case(
        self,
        mock_employee_price_repository,
        mock_timesheet_gateway,
        mock_employee_gateway,
    ):
        """Fixture que proporciona el caso de uso con todos los mocks."""
        return ListTeamEmployeePricesUseCase(
            mock_employee_price_repository,
            mock_timesheet_gateway,
            mock_employee_gateway,
        )

    @pytest.fixture
    def sample_current_employee(self):
        """Fixture que proporciona el empleado actual."""
        return Employee(
            id=1,
            email="current.user@test.com",
            full_name="Current User",
        )

    @pytest.fixture
    def sample_team_users(self):
        """Fixture que proporciona usuarios del equipo."""
        return [
            {
                "id": 10,
                "name": "John Doe",
                "work_email": "john.doe@test.com",
            },
            {
                "id": 20,
                "name": "Jane Smith",
                "work_email": "jane.smith@test.com",
            },
            {
                "id": 30,
                "name": "Bob Johnson",
                "work_email": "bob.johnson@test.com",
            },
        ]

    @pytest.fixture
    def sample_open_records(self):
        """Fixture que proporciona registros abiertos de precios."""
        return {
            10: EmployeePrice(
                id=1,
                user_id=10,
                date_from=date(2024, 1, 1),
                date_to=None,
                cost_per_hour=50.0,
            ),
            20: EmployeePrice(
                id=2,
                user_id=20,
                date_from=date(2024, 1, 1),
                date_to=None,
                cost_per_hour=60.0,
            ),
            30: EmployeePrice(
                id=3,
                user_id=30,
                date_from=date(2024, 1, 1),
                date_to=None,
                cost_per_hour=55.0,
            ),
        }

    def test_execute_returns_team_prices_successfully(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
        sample_open_records,
    ):
        """Test que verifica la obtención exitosa de precios del equipo."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = sample_team_users

        # Configurar respuestas del repositorio para cada empleado
        def get_open_record_side_effect(user_id):
            return sample_open_records.get(user_id)

        mock_employee_price_repository.get_open_record_by_user_id.side_effect = (
            get_open_record_side_effect
        )

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 3
        mock_employee_gateway.get_by_id.assert_called_once_with(user_id)
        mock_timesheet_gateway.get_team_users.assert_called_once_with(
            user_id, sample_current_employee.id
        )
        assert mock_employee_price_repository.get_open_record_by_user_id.call_count == 3

        # Verificar estructura de los resultados
        assert result[0]["employee_id"] == 10
        assert result[0]["name"] == "John Doe"
        assert result[0]["email"] == "john.doe@test.com"
        assert result[0]["cost_per_hour"] == 50.0
        assert result[0]["date_from"] == date(2024, 1, 1)
        assert result[0]["date_to"] is None

    def test_execute_returns_empty_list_when_no_team(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        sample_current_employee,
    ):
        """Test que verifica que se devuelve lista vacía cuando no hay equipo."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = []

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert result == []
        assert isinstance(result, list)
        assert len(result) == 0
        mock_employee_gateway.get_by_id.assert_called_once_with(user_id)
        mock_timesheet_gateway.get_team_users.assert_called_once_with(
            user_id, sample_current_employee.id
        )

    def test_execute_raises_value_error_when_no_employee(
        self, use_case, mock_employee_gateway
    ):
        """Test que verifica error cuando el usuario no tiene empleado asociado."""
        # Arrange
        user_id = 999

        mock_employee_gateway.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(user_id)

        assert "El usuario no tiene un empleado asociado" in str(exc_info.value)
        mock_employee_gateway.get_by_id.assert_called_once_with(user_id)

    def test_execute_with_team_members_without_open_records(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
    ):
        """Test que verifica el manejo de miembros del equipo sin registros abiertos."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = sample_team_users
        # Ningún empleado tiene registro abierto
        mock_employee_price_repository.get_open_record_by_user_id.return_value = None

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 3
        # Todos deberían tener cost_per_hour, date_from y date_to en None
        for employee_info in result:
            assert employee_info["cost_per_hour"] is None
            assert employee_info["date_from"] is None
            assert employee_info["date_to"] is None
            assert "employee_id" in employee_info
            assert "name" in employee_info
            assert "email" in employee_info

    def test_execute_with_mixed_open_records(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
        sample_open_records,
    ):
        """Test que verifica el manejo de equipo con algunos miembros con y sin registros."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = sample_team_users

        # Solo el primer empleado tiene registro abierto
        def get_open_record_side_effect(user_id):
            if user_id == 10:
                return sample_open_records[10]
            return None

        mock_employee_price_repository.get_open_record_by_user_id.side_effect = (
            get_open_record_side_effect
        )

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 3
        # Primer empleado tiene registro
        assert result[0]["employee_id"] == 10
        assert result[0]["cost_per_hour"] == 50.0
        # Segundo y tercer empleado no tienen registro
        assert result[1]["employee_id"] == 20
        assert result[1]["cost_per_hour"] is None
        assert result[2]["employee_id"] == 30
        assert result[2]["cost_per_hour"] is None

    def test_execute_with_single_team_member(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
    ):
        """Test que verifica la obtención con un solo miembro en el equipo."""
        # Arrange
        user_id = 1
        single_team = [
            {
                "id": 10,
                "name": "John Doe",
                "work_email": "john.doe@test.com",
            }
        ]
        open_record = EmployeePrice(
            id=1,
            user_id=10,
            date_from=date(2024, 1, 1),
            date_to=None,
            cost_per_hour=50.0,
        )

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = single_team
        mock_employee_price_repository.get_open_record_by_user_id.return_value = (
            open_record
        )

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 1
        assert result[0]["employee_id"] == 10
        assert result[0]["name"] == "John Doe"
        assert result[0]["cost_per_hour"] == 50.0

    def test_execute_with_large_team(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
    ):
        """Test que verifica el manejo de un equipo grande."""
        # Arrange
        user_id = 1
        # Crear equipo de 10 miembros
        large_team = []
        for i in range(10):
            large_team.append(
                {
                    "id": 100 + i,
                    "name": f"Employee {i}",
                    "work_email": f"employee{i}@test.com",
                }
            )

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = large_team
        mock_employee_price_repository.get_open_record_by_user_id.return_value = None

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 10
        assert mock_employee_price_repository.get_open_record_by_user_id.call_count == 10

    def test_execute_employee_gateway_exception_propagation(
        self, use_case, mock_employee_gateway
    ):
        """Test que verifica que las excepciones del employee_gateway se propagan."""
        # Arrange
        user_id = 1
        mock_employee_gateway.get_by_id.side_effect = Exception(
            "Database connection failed"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(user_id)

        assert "Database connection failed" in str(exc_info.value)
        mock_employee_gateway.get_by_id.assert_called_once_with(user_id)

    def test_execute_timesheet_gateway_exception_propagation(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        sample_current_employee,
    ):
        """Test que verifica que las excepciones del timesheet_gateway se propagan."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.side_effect = Exception(
            "Odoo connection failed"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(user_id)

        assert "Odoo connection failed" in str(exc_info.value)
        mock_timesheet_gateway.get_team_users.assert_called_once()

    def test_execute_employee_price_repository_exception_propagation(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
    ):
        """Test que verifica que las excepciones del repositorio de precios se propagan."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = sample_team_users
        mock_employee_price_repository.get_open_record_by_user_id.side_effect = (
            Exception("Repository error")
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(user_id)

        assert "Repository error" in str(exc_info.value)

    def test_execute_result_structure_is_correct(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
    ):
        """Test que verifica que la estructura del resultado es correcta."""
        # Arrange
        user_id = 1
        open_record = EmployeePrice(
            id=1,
            user_id=10,
            date_from=date(2024, 1, 1),
            date_to=None,
            cost_per_hour=50.0,
        )

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = [sample_team_users[0]]
        mock_employee_price_repository.get_open_record_by_user_id.return_value = (
            open_record
        )

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 1
        employee_info = result[0]
        # Verificar que tiene todas las claves requeridas
        assert "employee_id" in employee_info
        assert "name" in employee_info
        assert "email" in employee_info
        assert "cost_per_hour" in employee_info
        assert "date_from" in employee_info
        assert "date_to" in employee_info
        # Verificar tipos
        assert isinstance(employee_info["employee_id"], int)
        assert isinstance(employee_info["name"], str)
        assert isinstance(employee_info["email"], str)

    def test_execute_with_team_users_missing_fields(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
    ):
        """Test que verifica el manejo de usuarios con campos faltantes."""
        # Arrange
        user_id = 1
        incomplete_team = [
            {
                "id": 10,
                # Falta "name" y "work_email"
            }
        ]

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = incomplete_team
        mock_employee_price_repository.get_open_record_by_user_id.return_value = None

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 1
        # Debe usar valores por defecto vacíos
        assert result[0]["employee_id"] == 10
        assert result[0]["name"] == ""
        assert result[0]["email"] == ""

    def test_execute_with_different_user_ids(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
    ):
        """Test que verifica la ejecución con diferentes user_ids."""
        # Arrange
        user_id_1 = 100
        user_id_2 = 200

        employee_1 = Employee(id=1, email="user1@test.com", full_name="User 1")
        employee_2 = Employee(id=2, email="user2@test.com", full_name="User 2")

        team_1 = [{"id": 10, "name": "Team 1 Member", "work_email": "member1@test.com"}]
        team_2 = [{"id": 20, "name": "Team 2 Member", "work_email": "member2@test.com"}]

        # Act & Assert - Primer usuario
        mock_employee_gateway.get_by_id.return_value = employee_1
        mock_timesheet_gateway.get_team_users.return_value = team_1
        mock_employee_price_repository.get_open_record_by_user_id.return_value = None

        result_1 = use_case.execute(user_id_1)
        assert len(result_1) == 1
        assert result_1[0]["employee_id"] == 10
        mock_employee_gateway.get_by_id.assert_called_with(user_id_1)

        # Act & Assert - Segundo usuario
        mock_employee_gateway.get_by_id.return_value = employee_2
        mock_timesheet_gateway.get_team_users.return_value = team_2

        result_2 = use_case.execute(user_id_2)
        assert len(result_2) == 1
        assert result_2[0]["employee_id"] == 20
        mock_employee_gateway.get_by_id.assert_called_with(user_id_2)

    def test_execute_with_open_record_with_cost_per_hour_none(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
    ):
        """Test que verifica el manejo de registros abiertos con cost_per_hour=None."""
        # Arrange
        user_id = 1
        open_record_without_cost = EmployeePrice(
            id=1,
            user_id=10,
            date_from=date(2024, 1, 1),
            date_to=None,
            cost_per_hour=None,  # Sin costo definido
        )

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = [sample_team_users[0]]
        mock_employee_price_repository.get_open_record_by_user_id.return_value = (
            open_record_without_cost
        )

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 1
        assert result[0]["cost_per_hour"] is None
        assert result[0]["date_from"] == date(2024, 1, 1)
        assert result[0]["date_to"] is None

    def test_execute_with_varying_cost_per_hour_values(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
    ):
        """Test que verifica diferentes valores de cost_per_hour en el equipo."""
        # Arrange
        user_id = 1
        team = [
            {"id": 10, "name": "Employee 1", "work_email": "emp1@test.com"},
            {"id": 20, "name": "Employee 2", "work_email": "emp2@test.com"},
            {"id": 30, "name": "Employee 3", "work_email": "emp3@test.com"},
        ]

        records = {
            10: EmployeePrice(
                id=1, user_id=10, date_from=date(2024, 1, 1), date_to=None, cost_per_hour=50.50
            ),
            20: EmployeePrice(
                id=2, user_id=20, date_from=date(2024, 1, 1), date_to=None, cost_per_hour=100.0
            ),
            30: None,  # Sin registro
        }

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = team

        def get_open_record_side_effect(user_id):
            return records.get(user_id)

        mock_employee_price_repository.get_open_record_by_user_id.side_effect = (
            get_open_record_side_effect
        )

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 3
        assert result[0]["cost_per_hour"] == 50.50
        assert result[1]["cost_per_hour"] == 100.0
        assert result[2]["cost_per_hour"] is None

    def test_execute_preserves_team_order(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
    ):
        """Test que verifica que se preserva el orden de los miembros del equipo."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = sample_team_users
        mock_employee_price_repository.get_open_record_by_user_id.return_value = None

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 3
        # Verificar que el orden se mantiene
        assert result[0]["employee_id"] == 10
        assert result[1]["employee_id"] == 20
        assert result[2]["employee_id"] == 30

    def test_execute_calls_get_open_record_for_each_team_member(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
        sample_current_employee,
        sample_team_users,
    ):
        """Test que verifica que se llama get_open_record para cada miembro del equipo."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = sample_team_users
        mock_employee_price_repository.get_open_record_by_user_id.return_value = None

        # Act
        use_case.execute(user_id)

        # Assert
        # Debe haberse llamado 3 veces (una por cada miembro del equipo)
        assert mock_employee_price_repository.get_open_record_by_user_id.call_count == 3
        # Verificar que se llamó con los IDs correctos
        calls = mock_employee_price_repository.get_open_record_by_user_id.call_args_list
        assert calls[0][1]["user_id"] == 10
        assert calls[1][1]["user_id"] == 20
        assert calls[2][1]["user_id"] == 30

    def test_execute_with_zero_user_id(
        self, use_case, mock_employee_gateway
    ):
        """Test que verifica el comportamiento con user_id=0."""
        # Arrange
        user_id = 0
        mock_employee_gateway.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError):
            use_case.execute(user_id)

        mock_employee_gateway.get_by_id.assert_called_once_with(user_id)

    def test_execute_with_negative_user_id(
        self, use_case, mock_employee_gateway
    ):
        """Test que verifica el comportamiento con user_id negativo."""
        # Arrange
        user_id = -1
        mock_employee_gateway.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError):
            use_case.execute(user_id)

        mock_employee_gateway.get_by_id.assert_called_once_with(user_id)

    def test_execute_returns_list_type(
        self,
        use_case,
        mock_employee_gateway,
        mock_timesheet_gateway,
        sample_current_employee,
    ):
        """Test que verifica que el resultado es siempre una lista."""
        # Arrange
        user_id = 1

        mock_employee_gateway.get_by_id.return_value = sample_current_employee
        mock_timesheet_gateway.get_team_users.return_value = []

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert isinstance(result, list)

