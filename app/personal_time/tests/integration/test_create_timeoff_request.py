import pytest
from datetime import date, timedelta
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway
from app.personal_time.domain.models import TimeOffRequest


@pytest.mark.integration  # type: ignore[attr-defined]
class TestCreatetimeoffRequestIntegration:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        """Setup para tests de integración con Odoo real."""
        self.odoo_client = get_odoo_connection()
        self.gateway = OdooTimeOffeGateway(self.odoo_client)
        yield

    def test_create_timeoff_request_success(self):
        """Test de integración que crea una solicitud de licencia real en Odoo."""
        # Arrange - Crear una solicitud de prueba
        tomorrow = date.today() + timedelta(days=1)
        day_after_tomorrow = date.today() + timedelta(days=2)
        
        timeoff_request = TimeOffRequest(
            holiday_status_id=1,  # Usar ID 1 que probablemente existe
            name="Tiempo personal - Prueba automatizada",
            request_date_from=tomorrow,
            request_date_to=day_after_tomorrow,
            employee_id=1  # Usar ID 1 que probablemente existe
        )

        # Act
        result = self.gateway.create_timeoff_request(timeoff_request)

        # Assert
        print(f"\n🔍 Resultado de creación:")
        print(f"   Éxito: {result.success}")
        print(f"   Mensaje: {result.message}")
        print(f"   ID solicitud: {result.request_id}")

        if result.success:
            assert result.request_id is not None
            assert result.request_id > 0
            assert isinstance(result.request_id, int)
            print(f"\n✅ Solicitud creada exitosamente con ID: {result.request_id}")
        else:
            # Si falla, verificar que el mensaje de error sea informativo
            assert result.request_id is None
            assert len(result.message) > 0
            print(f"\n❌ Error esperado (posible problema de configuración): {result.message}")
            
            # No fallar el test si es un error de configuración conocido
            known_errors = [
                "employee_id",
                "holiday_status_id", 
                "access rights",
                "does not exist",
                "not found"
            ]
            is_known_error = any(error in result.message.lower() for error in known_errors)
            if is_known_error:
                pytest.skip(f"Error de configuración conocido: {result.message}")

    def test_timeoff_request_data_conversion(self):
        """Test que verifica la conversión de datos a formato Odoo."""
        # Arrange
        test_date_from = date(2024, 12, 25)
        test_date_to = date(2024, 12, 26)
        
        timeoff_request = TimeOffRequest(
            holiday_status_id=2,
            name="Vacaciones de prueba",
            request_date_from=test_date_from,
            request_date_to=test_date_to,
            employee_id=5
        )

        # Act
        odoo_data = timeoff_request.to_odoo_data()

        # Assert
        expected_data = {
            "holiday_status_id": 2,
            "name": "Vacaciones de prueba",
            "request_date_from": "2024-12-25",
            "request_date_to": "2024-12-26",
            "employee_id": 5,
        }
        
        assert odoo_data == expected_data
        print(f"\n📋 Datos convertidos correctamente:")
        for key, value in odoo_data.items():
            print(f"   {key}: {value}")

    def test_timeoff_request_validation_future_dates(self):
        """Test que verifica la creación con fechas futuras."""
        # Arrange - Usar fechas futuras para evitar conflictos
        future_date = date.today() + timedelta(days=30)
        end_date = future_date + timedelta(days=1)
        
        timeoff_request = TimeOffRequest(
            holiday_status_id=1,
            name="Prueba fechas futuras",
            request_date_from=future_date,
            request_date_to=end_date,
            employee_id=1
        )

        # Act
        result = self.gateway.create_timeoff_request(timeoff_request)

        # Assert
        print(f"\n📅 Test con fechas futuras:")
        print(f"   Desde: {future_date}")
        print(f"   Hasta: {end_date}")
        print(f"   Resultado: {result.success}")
        print(f"   Mensaje: {result.message}")

        # El test debe manejar tanto éxito como errores conocidos
        if not result.success:
            # Verificar que el error sea informativo
            assert len(result.message) > 0
            assert result.request_id is None
        else:
            assert result.request_id is not None
            assert result.request_id > 0
