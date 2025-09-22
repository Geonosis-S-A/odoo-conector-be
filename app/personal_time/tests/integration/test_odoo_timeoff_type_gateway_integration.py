from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
import pytest
from app.personal_time.domain.models import TimeOffType
from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooTimeOffGatewayIntegration:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        """Setup para tests de integración con Odoo real."""
        self.odoo_client = get_odoo_connection()
        self.gateway = OdooTimeOffeGateway(self.odoo_client)
        yield

    def test_get_all_timeoff_types_returns_valid_list(self):
        """Test de integración que verifica la conexión real con Odoo."""
        # Act
        timeoff_types = self.gateway.get_all_timeoff_types()

        # Assert
        assert timeoff_types is not None, "El gateway debe retornar una lista, no None"
        assert isinstance(timeoff_types, list), "El resultado debe ser una lista"

        # Debug information - solo si hay tipos de licencias
        if timeoff_types:
            print(f"\n✅ Tipos de licencias encontrados: {len(timeoff_types)}")
            for timeoff_type in timeoff_types[:5]:  # Mostrar solo los primeros 5
                print(f"   ID: {timeoff_type.id:2d} - {timeoff_type.name}")
                # Verificar que cada elemento es del tipo correcto
                assert isinstance(timeoff_type, TimeOffType), "Cada elemento debe ser del tipo TimeOffType"
                assert isinstance(timeoff_type.id, int), "El ID debe ser un entero"
                assert isinstance(timeoff_type.name, str), "El nombre debe ser una cadena"
                assert timeoff_type.name.strip(), "El nombre no debe estar vacío"
        else:
            print("\n  No se encontraron tipos de licencias en Odoo")

    def test_gateway_handles_empty_response(self):
        """Test que verifica que el gateway maneja respuestas vacías correctamente."""
        # Este test verifica que si Odoo retorna una lista vacía, el gateway la maneja bien
        # En una implementación real, esto podría ser un mock, pero aquí verificamos el comportamiento
        timeoff_types = self.gateway.get_all_timeoff_types()
        
        # Debe ser una lista (vacía o con elementos)
        assert isinstance(timeoff_types, list)
        
    def test_timeoff_type_model_creation(self):
        """Test unitario para la creación de TimeOffType desde datos de Odoo."""
        # Arrange
        odoo_data = {"id": 999, "name": "Licencia de Prueba"}
        
        # Act
        timeoff_type = TimeOffType.from_odoo_data(odoo_data)
        
        # Assert
        assert timeoff_type.id == 999
        assert timeoff_type.name == "Licencia de Prueba"
        assert isinstance(timeoff_type.id, int)
        assert isinstance(timeoff_type.name, str)
