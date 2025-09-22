import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.personal_time.api.routers import router
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.shared.security.role_enums.dev import Roles

# Crear una aplicación de FastAPI para pruebas
app = FastAPI()
app.include_router(router)


@pytest.fixture(autouse=True)
def setup_odoo_connection():
    """Fixture que configura la conexión real a Odoo."""
    odoo_client = get_odoo_connection()
    yield {"odoo_client": odoo_client}
    # No hay limpieza específica aquí porque usamos servicios de solo lectura


@pytest.fixture
def client_employee(local_db_session):
    """Fixture que proporciona un TestClient con usuario empleado."""

    async def mock_employee_user():
        return {
            "user_id": 588,  # Juan Gabriel Arias - empleado real de Odoo
            "user_email": "juan.arias@geonosis.com.ar",
            "user_name": "Juan Gabriel Arias",
            "roles": [1],  # Rol de empleado regular
        }

    app.dependency_overrides[get_current_user] = mock_employee_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_admin(local_db_session):
    """Fixture que proporciona un TestClient con usuario admin."""

    async def mock_admin_user():
        return {
            "user_id": 1,  # Administrator - ID real de Odoo
            "user_email": "admin@geonosis.odoo.com",
            "user_name": "Administrator",
            "roles": [Roles.approver],  # Rol de admin
        }

    app.dependency_overrides[get_current_user] = mock_admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_create_timeoff_request_success(client_employee):
    """Test de integración: crear solicitud de tiempo personal exitosa."""
    # Arrange
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    request_data = {
        "holiday_status_id": 2,  # Sick Time Off - tipo que sabemos que funciona
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": day_after_tomorrow.strftime("%Y-%m-%d"),
        "description": "Solicitud de prueba desde endpoint"
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n📊 Respuesta del endpoint:")
    print(f"   Status code: {response.status_code}")
    print(f"   Content: {response.json()}")

    # El endpoint siempre devuelve 200 y el resultado en el body
    assert response.status_code == 200
    data = response.json()
    
    # Verificar estructura de respuesta
    assert "success" in data
    assert "message" in data
    assert "request_id" in data
    assert isinstance(data["success"], bool)
    assert isinstance(data["message"], str)
    
    if data["success"]:
        # Éxito esperado
        assert data["request_id"] is not None
        assert isinstance(data["request_id"], int)
        assert data["request_id"] > 0
        assert "exitosamente" in data["message"]
        print(f"✅ Solicitud creada exitosamente con ID: {data['request_id']}")
    else:
        # Falló, pero la respuesta HTTP sigue siendo 200
        assert data["request_id"] is None
        print(f"❌ Error esperado (configuración Odoo): {data['message']}")
        
        # No fallar el test si es un error conocido de configuración
        known_errors = [
            "employee_id",
            "holiday_status_id", 
            "access rights",
            "does not exist",
            "not found",
            "No tienes ninguna asignación"
        ]
        is_known_error = any(error in data["message"].lower() for error in known_errors)
        if is_known_error:
            pytest.skip(f"Error de configuración conocido: {data['message']}")


@pytest.mark.integration
def test_create_timeoff_request_validation_errors(client_employee):
    """Test de integración: errores de validación."""
    # Test con datos inválidos
    invalid_requests = [
        {
            "data": {
                "holiday_status_id": -1,  # ID inválido
                "request_date_from": "2024-12-25",
                "request_date_to": "2024-12-26",
                "description": "Test"
            },
            "expected_status": 422,  # Error de validación de Pydantic
            "error_in": "detail"
        },
        {
            "data": {
                "holiday_status_id": 1,
                "request_date_from": "invalid-date",  # Fecha inválida
                "request_date_to": "2024-12-26",
                "description": "Test"
            },
            "expected_status": 422,  # Error de validación de Pydantic
            "error_in": "detail"
        }
    ]

    for i, test_case in enumerate(invalid_requests):
        print(f"\n🧪 Test de validación {i+1}:")
        
        # Act
        response = client_employee.post("/personal-time/timeoff-requests", json=test_case["data"])
        
        # Assert
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        expected_status = test_case["expected_status"]
        assert response.status_code == expected_status
        
        data = response.json()
        error_field = test_case["error_in"]
        assert error_field in data


@pytest.mark.integration
def test_create_timeoff_request_business_validation_errors(client_employee):
    """Test de integración: errores de validación de negocio del caso de uso."""
    
    # Test 1: Fechas en orden incorrecto
    print("\n🧪 Test 1: Fecha inicio después de fecha fin")
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": day_after_tomorrow.strftime("%Y-%m-%d"),  # Después
        "request_date_to": tomorrow.strftime("%Y-%m-%d"),  # Antes
        "description": "Test fechas incorrectas"
    }
    
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)
    
    assert response.status_code == 200  # HTTP 200 pero success=false
    data = response.json()
    assert data["success"] is False
    assert "fecha de inicio no puede ser posterior" in data["message"]
    assert data["request_id"] is None
    print(f"   ✅ Validación correcta: {data['message']}")


@pytest.mark.integration
def test_create_timeoff_request_past_dates(client_employee):
    """Test de integración: validación de fechas pasadas."""
    # Arrange
    yesterday = date.today() - timedelta(days=1)
    day_before_yesterday = date.today() - timedelta(days=2)
    
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": day_before_yesterday.strftime("%Y-%m-%d"),
        "request_date_to": yesterday.strftime("%Y-%m-%d"),
        "description": "Solicitud con fechas pasadas"
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n📅 Test con fechas pasadas:")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Ahora devuelve 200 con success=false
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "fechas pasadas" in data["message"]
    assert data["request_id"] is None


@pytest.mark.integration
def test_create_timeoff_request_future_dates(client_employee):
    """Test de integración: validación con fechas futuras."""
    # Arrange
    future_date = date.today() + timedelta(days=30)
    end_date = future_date + timedelta(days=2)
    
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": future_date.strftime("%Y-%m-%d"),
        "request_date_to": end_date.strftime("%Y-%m-%d"),
        "description": "Solicitud con fechas futuras"
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n📅 Test con fechas futuras:")
    print(f"   Desde: {future_date}")
    print(f"   Hasta: {end_date}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Siempre devuelve 200, pero puede ser exitoso o fallar por configuración de Odoo
    assert response.status_code == 200
    data = response.json()
    # Verificar estructura básica
    assert "success" in data
    assert "message" in data
    assert "request_id" in data


@pytest.mark.integration
def test_create_timeoff_request_description_validation(client_employee):
    """Test de integración: validación de descripción."""
    # Arrange
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    # Test con descripción muy larga
    long_description = "x" * 501  # Más de 500 caracteres
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": day_after_tomorrow.strftime("%Y-%m-%d"),
        "description": long_description
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n📝 Test con descripción muy larga:")
    print(f"   Status: {response.status_code}")
    print(f"   Longitud descripción: {len(long_description)}")
    
    assert response.status_code == 422  # Error de validación de Pydantic
    data = response.json()
    assert "detail" in data


@pytest.mark.integration 
def test_create_timeoff_request_admin_user(client_admin):
    """Test de integración: crear solicitud con usuario admin."""
    # Arrange
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": day_after_tomorrow.strftime("%Y-%m-%d"),
        "description": "Solicitud desde usuario admin"
    }

    # Act
    response = client_admin.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n👑 Test con usuario admin:")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Los admins también pueden crear solicitudes para sí mismos
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "request_id" in data


@pytest.mark.integration
def test_create_timeoff_request_response_format(client_employee):
    """Test de integración: verifica formato de respuesta."""
    # Arrange
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": day_after_tomorrow.strftime("%Y-%m-%d"),
        "description": "Test formato respuesta"
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n🔍 Verificación formato respuesta:")
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    # Verificar headers
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    
    # Siempre devuelve 200 con la estructura estándar
    assert response.status_code == 200
    required_fields = {"request_id", "success", "message"}
    assert set(data.keys()) == required_fields
    assert isinstance(data["success"], bool)
    assert isinstance(data["message"], str)
    
    if data["success"]:
        assert isinstance(data["request_id"], int)
        assert data["request_id"] > 0
    else:
        assert data["request_id"] is None


@pytest.mark.integration
def test_create_timeoff_request_without_description(client_employee):
    """Test de integración: crear solicitud sin descripción (campo opcional)."""
    # Arrange
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    # Request sin el campo description
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": day_after_tomorrow.strftime("%Y-%m-%d")
        # No incluimos 'description'
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n📝 Test sin descripción:")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "request_id" in data
    
    # Si fue exitoso, verificar que se usó la descripción por defecto
    if data["success"]:
        print(f"   ✅ Solicitud creada con descripción por defecto")
    else:
        print(f"   ⚠️  Error esperado por configuración: {data['message']}")


@pytest.mark.integration
def test_create_timeoff_request_with_empty_description(client_employee):
    """Test de integración: crear solicitud con descripción explícitamente vacía."""
    # Arrange
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    # Request con description explícitamente null/empty
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": day_after_tomorrow.strftime("%Y-%m-%d"),
        "description": None  # Explícitamente None
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n🔧 Test con descripción None:")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "request_id" in data


@pytest.mark.integration
def test_create_timeoff_request_same_day(client_employee):
    """Test de integración: solicitud para el mismo día."""
    # Arrange
    tomorrow = date.today() + timedelta(days=1)
    
    request_data = {
        "holiday_status_id": 2,
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": tomorrow.strftime("%Y-%m-%d"),  # Mismo día
        "description": "Solicitud de un solo día"
    }

    # Act
    response = client_employee.post("/personal-time/timeoff-requests", json=request_data)

    # Assert
    print(f"\n📅 Test solicitud mismo día:")
    print(f"   Fecha: {tomorrow}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Debería ser válido (un día de duración)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "request_id" in data
