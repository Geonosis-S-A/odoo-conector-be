from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
import pytest
from app.personal_time.domain.models import LeaveType
from app.personal_time.infra.external.odoo_leave_type_gateway import OdooLeaveTypeGateway


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooLeaveTypeGateway:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.odoo_client = get_odoo_connection()
        self.gateway = OdooLeaveTypeGateway(self.odoo_client)
        yield

    def test_get_all_leave_types_returns_list(self):
        """Test que verifica que get_all_leave_types() retorna una lista de tipos de licencias."""
        # Act
        leave_types = self.gateway.get_all_leave_types()

        # Assert
        assert leave_types is not None, "El gateway debe retornar una lista, no None"
        assert isinstance(leave_types, list), "El resultado debe ser una lista"

        # Debug information - solo si hay tipos de licencias
        if leave_types:
            print(f"\nTipos de licencias encontrados: {len(leave_types)}")
            for leave_type in leave_types[:5]:  # Mostrar solo los primeros 5
                print(f"ID: {leave_type.id}, Nombre: {leave_type.name}")
                # Verificar que cada elemento es del tipo correcto
                assert isinstance(leave_type, LeaveType), "Cada elemento debe ser del tipo LeaveType"
                assert isinstance(leave_type.id, int), "El ID debe ser un entero"
                assert isinstance(leave_type.name, str), "El nombre debe ser una cadena"
        else:
            print("\nNo se encontraron tipos de licencias")

    def test_leave_type_from_odoo_data(self):
        """Test que verifica la creación de LeaveType desde datos de Odoo."""
        # Arrange
        odoo_data = {"id": 1, "name": "Vacaciones"}
        
        # Act
        leave_type = LeaveType.from_odoo_data(odoo_data)
        
        # Assert
        assert leave_type.id == 1
        assert leave_type.name == "Vacaciones"
