import pytest
from unittest.mock import Mock
from app.personal_time.application.use_cases.get_timeoff_types import GetTimeOffTypesUseCase
from app.personal_time.domain.models import TimeOffType
from app.personal_time.domain.gateway import TimeOffGateway


class TestGetTimeOffTypesUseCase:
    """Tests unitarios para el caso de uso GetTimeOffTypesUseCase."""

    def test_execute_returns_timeoff_types_successfully(self):
        """Test que verifica que execute() retorna tipos de licencias exitosamente."""
        # Arrange
        mock_gateway = Mock(spec=TimeOffGateway)
        expected_timeoff_types = [
            TimeOffType(id=1, name="Vacaciones"),
            TimeOffType(id=2, name="Licencia por enfermedad"),
            TimeOffType(id=3, name="Licencia de paternidad"),
        ]
        mock_gateway.get_all_timeoff_types.return_value = expected_timeoff_types
        
        use_case = GetTimeOffTypesUseCase(mock_gateway)
        
        # Act
        result = use_case.execute()
        
        # Assert
        assert result == expected_timeoff_types
        mock_gateway.get_all_timeoff_types.assert_called_once()

    def test_execute_returns_empty_list_when_no_timeoff_types(self):
        """Test que verifica que execute() maneja correctamente cuando no hay tipos de licencias."""
        # Arrange
        mock_gateway = Mock(spec=TimeOffGateway)
        mock_gateway.get_all_timeoff_types.return_value = []
        
        use_case = GetTimeOffTypesUseCase(mock_gateway)
        
        # Act
        result = use_case.execute()
        
        # Assert
        assert result == []
        assert isinstance(result, list)
        mock_gateway.get_all_timeoff_types.assert_called_once()

    def test_execute_raises_exception_when_gateway_fails(self):
        """Test que verifica que execute() propaga excepciones del gateway."""
        # Arrange
        mock_gateway = Mock(spec=TimeOffGateway)
        gateway_error = Exception("Error de conexión con Odoo")
        mock_gateway.get_all_timeoff_types.side_effect = gateway_error
        
        use_case = GetTimeOffTypesUseCase(mock_gateway)
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute()
        
        assert "Error en el caso de uso GetTimeOffTypes" in str(exc_info.value)
        assert "Error de conexión con Odoo" in str(exc_info.value)
        mock_gateway.get_all_timeoff_types.assert_called_once()

    def test_execute_with_large_dataset(self):
        """Test que verifica que execute() maneja grandes volúmenes de datos."""
        # Arrange
        mock_gateway = Mock(spec=TimeOffGateway)
        large_dataset = [
            TimeOffType(id=i, name=f"Tipo de licencia {i}")
            for i in range(1, 101)  # 100 tipos de licencias
        ]
        mock_gateway.get_all_timeoff_types.return_value = large_dataset
        
        use_case = GetTimeOffTypesUseCase(mock_gateway)
        
        # Act
        result = use_case.execute()
        
        # Assert
        assert len(result) == 100
        assert all(isinstance(timeoff_type, TimeOffType) for timeoff_type in result)
        assert result[0].name == "Tipo de licencia 1"
        assert result[-1].name == "Tipo de licencia 100"
        mock_gateway.get_all_timeoff_types.assert_called_once()

    def test_use_case_initialization(self):
        """Test que verifica la correcta inicialización del caso de uso."""
        # Arrange
        mock_gateway = Mock(spec=TimeOffGateway)
        
        # Act
        use_case = GetTimeOffTypesUseCase(mock_gateway)
        
        # Assert
        assert use_case.timeoff_gateway is mock_gateway
        assert hasattr(use_case, 'execute')

    def test_use_case_is_stateless(self):
        """Test que verifica que el caso de uso es stateless (sin estado)."""
        # Arrange
        mock_gateway = Mock(spec=TimeOffGateway)
        timeoff_types = [TimeOffType(id=1, name="Test")]
        mock_gateway.get_all_timeoff_types.return_value = timeoff_types
        
        use_case = GetTimeOffTypesUseCase(mock_gateway)
        
        # Act - Ejecutar múltiples veces
        result1 = use_case.execute()
        result2 = use_case.execute()
        
        # Assert - Los resultados deben ser consistentes
        assert result1 == result2
        assert mock_gateway.get_all_timeoff_types.call_count == 2
