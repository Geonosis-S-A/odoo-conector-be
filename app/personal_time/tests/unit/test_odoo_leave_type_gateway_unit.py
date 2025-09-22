import pytest
from unittest.mock import Mock, MagicMock
from app.personal_time.infra.external.odoo_leave_type_gateway import OdooLeaveTypeGateway
from app.personal_time.domain.models import LeaveType


class TestOdooLeaveTypeGateway:
    """Tests unitarios para OdooLeaveTypeGateway usando mocks."""

    @pytest.fixture
    def mock_odoo_connection(self):
        """Fixture que proporciona una conexión mock de Odoo."""
        mock_connection = {
            "uid": 1,
            "models": Mock(),
            "ODOO_DB": "test_db",
            "ODOO_PASSWORD": "test_password"
        }
        return mock_connection

    @pytest.fixture
    def gateway(self, mock_odoo_connection):
        """Fixture que proporciona una instancia del gateway con conexión mock."""
        return OdooLeaveTypeGateway(mock_odoo_connection)

    def test_get_all_leave_types_success(self, gateway, mock_odoo_connection):
        """Test que verifica el flujo exitoso de obtención de tipos de licencias."""
        # Arrange
        mock_odoo_data = [
            {"id": 1, "name": "Vacaciones"},
            {"id": 2, "name": "Licencia por enfermedad"},
            {"id": 3, "name": "Licencia de paternidad"},
        ]
        mock_odoo_connection["models"].execute_kw.return_value = mock_odoo_data

        # Act
        result = gateway.get_all_leave_types()

        # Assert
        assert len(result) == 3
        assert all(isinstance(leave_type, LeaveType) for leave_type in result)
        
        # Verificar los datos específicos
        assert result[0].id == 1
        assert result[0].name == "Vacaciones"
        assert result[1].id == 2
        assert result[1].name == "Licencia por enfermedad"
        assert result[2].id == 3
        assert result[2].name == "Licencia de paternidad"

        # Verificar que se llamó a Odoo con los parámetros correctos
        mock_odoo_connection["models"].execute_kw.assert_called_once_with(
            "test_db",
            1,
            "test_password",
            "hr.leave.type",
            "search_read",
            [[]],
            {"fields": ["id", "name"]}
        )

    def test_get_all_leave_types_empty_result(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo de respuesta vacía de Odoo."""
        # Arrange
        mock_odoo_connection["models"].execute_kw.return_value = []

        # Act
        result = gateway.get_all_leave_types()

        # Assert
        assert result == []
        assert isinstance(result, list)
        mock_odoo_connection["models"].execute_kw.assert_called_once()

    def test_get_all_leave_types_invalid_response_type(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo de respuesta inválida de Odoo."""
        # Arrange
        mock_odoo_connection["models"].execute_kw.return_value = "invalid_response"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            gateway.get_all_leave_types()
        
        assert "Respuesta inesperada de Odoo: se esperaba una lista" in str(exc_info.value)

    def test_get_all_leave_types_odoo_exception(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo de excepciones de Odoo."""
        # Arrange
        odoo_error = Exception("Error de conexión XML-RPC")
        mock_odoo_connection["models"].execute_kw.side_effect = odoo_error

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            gateway.get_all_leave_types()
        
        assert "Error al obtener tipos de licencias desde Odoo" in str(exc_info.value)
        assert "Error de conexión XML-RPC" in str(exc_info.value)

    def test_get_all_leave_types_none_response(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo cuando Odoo retorna None."""
        # Arrange
        mock_odoo_connection["models"].execute_kw.return_value = None

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            gateway.get_all_leave_types()
        
        assert "Respuesta inesperada de Odoo: se esperaba una lista" in str(exc_info.value)

    def test_get_all_leave_types_malformed_data(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo de datos malformados de Odoo."""
        # Arrange - Datos sin el campo 'name'
        mock_odoo_data = [
            {"id": 1, "name": "Vacaciones"},
            {"id": 2},  # Falta el campo 'name'
        ]
        mock_odoo_connection["models"].execute_kw.return_value = mock_odoo_data

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            gateway.get_all_leave_types()
        
        assert "Error al obtener tipos de licencias desde Odoo" in str(exc_info.value)

    def test_get_all_leave_types_large_dataset(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo de grandes volúmenes de datos."""
        # Arrange
        large_dataset = [
            {"id": i, "name": f"Tipo de licencia {i}"}
            for i in range(1, 1001)  # 1000 tipos
        ]
        mock_odoo_connection["models"].execute_kw.return_value = large_dataset

        # Act
        result = gateway.get_all_leave_types()

        # Assert
        assert len(result) == 1000
        assert all(isinstance(leave_type, LeaveType) for leave_type in result)
        assert result[0].name == "Tipo de licencia 1"
        assert result[-1].name == "Tipo de licencia 1000"

    def test_gateway_initialization(self, mock_odoo_connection):
        """Test que verifica la correcta inicialización del gateway."""
        # Act
        gateway = OdooLeaveTypeGateway(mock_odoo_connection)

        # Assert
        assert gateway.odoo_connection == mock_odoo_connection
        assert hasattr(gateway, 'get_all_leave_types')

    def test_get_all_leave_types_special_characters(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo de nombres con caracteres especiales."""
        # Arrange
        mock_odoo_data = [
            {"id": 1, "name": "Licencia por Maternidad/Paternidad"},
            {"id": 2, "name": "Permiso extraordinario (especial)"},
            {"id": 3, "name": "Ausencia médica - COVID-19"},
        ]
        mock_odoo_connection["models"].execute_kw.return_value = mock_odoo_data

        # Act
        result = gateway.get_all_leave_types()

        # Assert
        assert len(result) == 3
        assert result[0].name == "Licencia por Maternidad/Paternidad"
        assert result[1].name == "Permiso extraordinario (especial)"
        assert result[2].name == "Ausencia médica - COVID-19"

    def test_get_all_leave_types_unicode_characters(self, gateway, mock_odoo_connection):
        """Test que verifica el manejo de caracteres Unicode."""
        # Arrange
        mock_odoo_data = [
            {"id": 1, "name": "Licencia médica"},
            {"id": 2, "name": "Permiso de estudio académico"},
            {"id": 3, "name": "Ausencia por duelo"},
        ]
        mock_odoo_connection["models"].execute_kw.return_value = mock_odoo_data

        # Act
        result = gateway.get_all_leave_types()

        # Assert
        assert len(result) == 3
        assert all(isinstance(leave_type.name, str) for leave_type in result)
        assert "médica" in result[0].name
        assert "académico" in result[1].name

    def test_get_all_leave_types_consistent_calls(self, gateway, mock_odoo_connection):
        """Test que verifica que las llamadas múltiples son consistentes."""
        # Arrange
        mock_odoo_data = [{"id": 1, "name": "Vacaciones"}]
        mock_odoo_connection["models"].execute_kw.return_value = mock_odoo_data

        # Act
        result1 = gateway.get_all_leave_types()
        result2 = gateway.get_all_leave_types()

        # Assert
        assert result1 == result2
        assert mock_odoo_connection["models"].execute_kw.call_count == 2
        
        # Verificar que ambas llamadas usan los mismos parámetros
        calls = mock_odoo_connection["models"].execute_kw.call_args_list
        assert calls[0] == calls[1]
