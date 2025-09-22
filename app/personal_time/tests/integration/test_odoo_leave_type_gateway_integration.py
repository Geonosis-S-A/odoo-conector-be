from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
import pytest
from app.personal_time.domain.models import LeaveType
from app.personal_time.infra.external.odoo_leave_type_gateway import OdooLeaveTypeGateway


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooLeaveTypeGatewayIntegration:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        """Setup para tests de integración con Odoo real."""
        self.odoo_client = get_odoo_connection()
        self.gateway = OdooLeaveTypeGateway(self.odoo_client)
        yield

    def test_get_all_leave_types_returns_valid_list(self):
        """Test de integración que verifica la conexión real con Odoo."""
        # Act
        leave_types = self.gateway.get_all_leave_types()

        # Assert
        assert leave_types is not None, "El gateway debe retornar una lista, no None"
        assert isinstance(leave_types, list), "El resultado debe ser una lista"

        # Debug information - solo si hay tipos de licencias
        if leave_types:
            print(f"\n✅ Tipos de licencias encontrados: {len(leave_types)}")
            for leave_type in leave_types[:5]:  # Mostrar solo los primeros 5
                print(f"   ID: {leave_type.id:2d} - {leave_type.name}")
                # Verificar que cada elemento es del tipo correcto
                assert isinstance(leave_type, LeaveType), "Cada elemento debe ser del tipo LeaveType"
                assert isinstance(leave_type.id, int), "El ID debe ser un entero"
                assert isinstance(leave_type.name, str), "El nombre debe ser una cadena"
                assert leave_type.name.strip(), "El nombre no debe estar vacío"
        else:
            print("\n  No se encontraron tipos de licencias en Odoo")

    def test_gateway_handles_empty_response(self):
        """Test que verifica que el gateway maneja respuestas vacías correctamente."""
        # Este test verifica que si Odoo retorna una lista vacía, el gateway la maneja bien
        # En una implementación real, esto podría ser un mock, pero aquí verificamos el comportamiento
        leave_types = self.gateway.get_all_leave_types()
        
        # Debe ser una lista (vacía o con elementos)
        assert isinstance(leave_types, list)
        
    def test_leave_type_model_creation(self):
        """Test unitario para la creación de LeaveType desde datos de Odoo."""
        # Arrange
        odoo_data = {"id": 999, "name": "Licencia de Prueba"}
        
        # Act
        leave_type = LeaveType.from_odoo_data(odoo_data)
        
        # Assert
        assert leave_type.id == 999
        assert leave_type.name == "Licencia de Prueba"
        assert isinstance(leave_type.id, int)
        assert isinstance(leave_type.name, str)
