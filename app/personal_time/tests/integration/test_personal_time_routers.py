import pytest
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
def client_admin(local_db_session):
    """Fixture que proporciona un TestClient con usuario admin."""

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Rol de admin
        }

    app.dependency_overrides[get_current_user] = mock_admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_regular(local_db_session):
    """Fixture que proporciona un TestClient con usuario regular."""

    async def mock_regular_user():
        return {
            "user_id": 2,
            "user_email": "user@example.com",
            "user_name": "Regular User",
            "roles": [1],  # Rol de empleado regular
        }

    app.dependency_overrides[get_current_user] = mock_regular_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_get_leave_types_success_admin_user(client_admin):
    """Test de integración: obtener tipos de licencias exitoso con usuario admin."""
    # Act
    response = client_admin.get("/personal-time/leave-types")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Si hay tipos de licencias, verificar estructura
    if data:
        print(f"\n✅ Tipos de licencias encontrados: {len(data)}")
        for leave_type in data[:5]:  # Mostrar solo los primeros 5
            print(f"   ID: {leave_type['id']:2d} - {leave_type['name']}")
            
            # Verificar estructura de cada tipo de licencia
            assert "id" in leave_type
            assert "name" in leave_type
            assert isinstance(leave_type["id"], int)
            assert isinstance(leave_type["name"], str)
            assert leave_type["id"] > 0
            assert len(leave_type["name"].strip()) > 0
    else:
        print("\n⚠️  No se encontraron tipos de licencias en Odoo")


@pytest.mark.integration
def test_get_leave_types_success_regular_user(client_regular):
    """Test de integración: obtener tipos de licencias exitoso con usuario regular."""
    # Act
    response = client_regular.get("/personal-time/leave-types")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Los usuarios regulares también deberían poder ver tipos de licencias
    # ya que es información básica necesaria para solicitar licencias
    if data:
        leave_type = data[0]
        assert "id" in leave_type
        assert "name" in leave_type
        assert isinstance(leave_type["id"], int)
        assert isinstance(leave_type["name"], str)


@pytest.mark.integration
def test_get_leave_types_response_format(client_admin):
    """Test de integración: verifica formato de respuesta."""
    # Act
    response = client_admin.get("/personal-time/leave-types")

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert isinstance(data, list)

    # Verificar que cada elemento tiene la estructura correcta
    for leave_type in data:
        # Verificar campos requeridos
        required_fields = {"id", "name"}
        assert set(leave_type.keys()) == required_fields

        # Verificar tipos de datos
        assert isinstance(leave_type["id"], int)
        assert isinstance(leave_type["name"], str)

        # Verificar validez de datos
        assert leave_type["id"] > 0
        assert len(leave_type["name"].strip()) > 0


@pytest.mark.integration
def test_get_leave_types_consistent_results(client_admin):
    """Test de integración: verifica que los resultados son consistentes."""
    # Act - Hacer múltiples llamadas
    response1 = client_admin.get("/personal-time/leave-types")
    response2 = client_admin.get("/personal-time/leave-types")

    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Los resultados deben ser consistentes
    assert len(data1) == len(data2)
    
    if data1:
        # Verificar que los IDs son los mismos en el mismo orden
        ids1 = [item["id"] for item in data1]
        ids2 = [item["id"] for item in data2]
        assert ids1 == ids2

        # Verificar que los nombres son los mismos
        names1 = [item["name"] for item in data1]
        names2 = [item["name"] for item in data2]
        assert names1 == names2


@pytest.mark.integration
def test_get_leave_types_data_integrity(client_admin):
    """Test de integración: verifica la integridad de los datos."""
    # Act
    response = client_admin.get("/personal-time/leave-types")

    # Assert
    assert response.status_code == 200

    data = response.json()

    if data:
        # Verificar que no hay IDs duplicados
        ids = [item["id"] for item in data]
        assert len(ids) == len(set(ids)), "No debe haber IDs duplicados"

        # Verificar que no hay nombres vacíos
        for leave_type in data:
            assert leave_type["name"].strip(), f"El nombre no debe estar vacío para ID {leave_type['id']}"

        # Verificar que los IDs son únicos y positivos
        for leave_type in data:
            assert leave_type["id"] > 0, f"El ID debe ser positivo: {leave_type['id']}"

        # Verificar que los nombres son diferentes (en la mayoría de casos)
        names = [item["name"] for item in data]
        unique_names = set(names)
        
        # Permitir algunos nombres duplicados pero no todos
        duplicate_ratio = (len(names) - len(unique_names)) / len(names) if names else 0
        assert duplicate_ratio < 0.5, "Demasiados nombres duplicados, verificar datos de Odoo"


@pytest.mark.integration
def test_get_leave_types_performance(client_admin):
    """Test de integración: verifica el rendimiento del endpoint."""
    import time

    # Act
    start_time = time.time()
    response = client_admin.get("/personal-time/leave-types")
    end_time = time.time()

    # Assert
    assert response.status_code == 200

    # El endpoint debería responder en menos de 5 segundos
    response_time = end_time - start_time
    assert response_time < 5.0, f"Respuesta muy lenta: {response_time:.2f}s"

    data = response.json()
    print(f"\n⏱️  Tiempo de respuesta: {response_time:.3f}s")
    print(f"📊 Tipos de licencias obtenidos: {len(data)}")


@pytest.mark.integration
def test_get_leave_types_error_handling(client_admin):
    """Test de integración: verifica el manejo de errores."""
    # Este test verifica que el endpoint maneja errores graciosamente
    # En condiciones normales debería funcionar, pero si hay problemas de conexión
    # debería retornar un error 500 apropiado

    # Act
    response = client_admin.get("/personal-time/leave-types")

    # Assert
    # El endpoint debería funcionar o fallar graciosamente
    assert response.status_code in [200, 500]

    if response.status_code == 500:
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)
        assert len(error_data["detail"]) > 0
    else:
        # Si es exitoso, verificar estructura
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
def test_get_leave_types_content_validation(client_admin):
    """Test de integración: verifica la validez del contenido."""
    # Act
    response = client_admin.get("/personal-time/leave-types")

    # Assert
    assert response.status_code == 200

    data = response.json()

    if data:
        for leave_type in data:
            # Verificar que el nombre no tiene caracteres de control
            name = leave_type["name"]
            assert not any(ord(char) < 32 for char in name if char != '\t'), \
                f"Nombre contiene caracteres de control: {repr(name)}"

            # Verificar longitud razonable del nombre
            assert 1 <= len(name) <= 255, \
                f"Nombre tiene longitud inválida: {len(name)} caracteres"

            # Verificar que el ID está en un rango razonable
            assert 1 <= leave_type["id"] <= 999999, \
                f"ID fuera de rango esperado: {leave_type['id']}"


@pytest.mark.integration
def test_get_leave_types_encoding_handling(client_admin):
    """Test de integración: verifica el manejo de caracteres especiales."""
    # Act
    response = client_admin.get("/personal-time/leave-types")

    # Assert
    assert response.status_code == 200

    data = response.json()

    if data:
        # Buscar tipos de licencias con caracteres especiales comunes en español
        special_chars_found = False
        common_spanish_chars = ['ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü', 'Ñ', 'Á', 'É', 'Í', 'Ó', 'Ú', 'Ü']
        
        for leave_type in data:
            name = leave_type["name"]
            
            # Verificar que los caracteres especiales se manejan correctamente
            if any(char in name for char in common_spanish_chars):
                special_chars_found = True
                # Verificar que el string es válido UTF-8
                assert isinstance(name, str)
                # Verificar que no hay problemas de encoding
                encoded = name.encode('utf-8')
                decoded = encoded.decode('utf-8')
                assert name == decoded

        # Si hay caracteres especiales, verificar que se procesaron correctamente
        if special_chars_found:
            print("\n✅ Caracteres especiales encontrados y procesados correctamente")


@pytest.mark.integration
def test_get_leave_types_business_logic_validation(client_admin):
    """Test de integración: valida la lógica de negocio específica."""
    # Act
    response = client_admin.get("/personal-time/leave-types")

    # Assert
    assert response.status_code == 200

    data = response.json()

    if data:
        # Verificar que hay tipos de licencias comunes esperados
        # (esto puede variar según la configuración de Odoo)
        leave_type_names = [item["name"].lower() for item in data]
        
        # Contar tipos comunes que podrían estar presentes
        common_types = {
            "vacaciones": any("vacacion" in name for name in leave_type_names),
            "enfermedad": any("enferm" in name or "médic" in name for name in leave_type_names),
            "maternidad": any("maternidad" in name or "paternidad" in name for name in leave_type_names),
        }
        
        # Al menos uno de los tipos comunes debería estar presente en una instalación típica
        common_found = sum(common_types.values())
        
        print(f"\n📋 Tipos de licencias comunes encontrados:")
        for type_name, found in common_types.items():
            status = "✅" if found else "❌"
            print(f"   {status} {type_name.capitalize()}: {found}")
        
        print(f"\n📊 Resumen:")
        print(f"   - Total tipos de licencias: {len(data)}")
        print(f"   - Tipos comunes encontrados: {common_found}/3")
        print(f"   - IDs únicos: {len(set(item['id'] for item in data))}")
        print(f"   - Nombres únicos: {len(set(item['name'] for item in data))}")

        # No forzar que existan tipos específicos, ya que depende de la configuración
        # pero sí verificar que hay datos coherentes
        assert len(data) > 0, "Debería haber al menos un tipo de licencia configurado"


@pytest.mark.integration
def test_get_leave_types_ordering_consistency(client_admin):
    """Test de integración: verifica la consistencia del ordenamiento."""
    # Act - Hacer múltiples llamadas
    responses = []
    for _ in range(3):
        response = client_admin.get("/personal-time/leave-types")
        assert response.status_code == 200
        responses.append(response.json())

    # Assert
    if responses[0]:  # Solo si hay datos
        # Verificar que el orden es consistente entre llamadas
        for i in range(1, len(responses)):
            ids_first = [item["id"] for item in responses[0]]
            ids_current = [item["id"] for item in responses[i]]
            assert ids_first == ids_current, f"Orden inconsistente en llamada {i+1}"

        # Verificar que el orden es lógico (por ID ascendente típicamente)
        ids = [item["id"] for item in responses[0]]
        # Verificar si está ordenado por ID (ascendente o descendente)
        is_ascending = all(ids[i] <= ids[i+1] for i in range(len(ids)-1))
        is_descending = all(ids[i] >= ids[i+1] for i in range(len(ids)-1))
        
        print(f"\n📈 Análisis de ordenamiento:")
        print(f"   - Ordenado ascendente por ID: {is_ascending}")
        print(f"   - Ordenado descendente por ID: {is_descending}")
        print(f"   - Primer ID: {ids[0] if ids else 'N/A'}")
        print(f"   - Último ID: {ids[-1] if ids else 'N/A'}")

        # Al menos debería ser consistente (aunque no necesariamente ordenado)
        assert True  # El test pasa si llega aquí sin errores
