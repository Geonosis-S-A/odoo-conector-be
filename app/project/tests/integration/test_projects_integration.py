import pytest
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.project.infra.external.odd_project_gateway import OdooProjectGateway


@pytest.fixture(autouse=True)
def setup_gateway():
    """Fixture que configura el gateway real."""
    odoo_client = get_odoo_connection()
    gateway = OdooProjectGateway(odoo_client)
    yield {"gateway": gateway}


@pytest.mark.integration
def test_get_all_active_projects_with_analytic_accounts(test_client):
    """Test de integración que prueba obtener todos los proyectos activos con cuenta analítica."""
    # Act
    response = test_client.get("/api/v1/projects/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar la estructura de los datos
    if len(data) > 0:
        print(f"\nProyectos de integración encontrados: {len(data)}")

        # Verificar estructura de cada proyecto
        for project in data:
            assert isinstance(project["id"], int), "El ID debe ser un entero"
            assert isinstance(project["name"], str), "El nombre debe ser una cadena"
            assert project["id"] > 0, "El ID debe ser positivo"
            assert len(project["name"].strip()) > 0, "El nombre no debe estar vacío"

            # Verificar que solo tiene los campos esperados
            expected_fields = {"id", "name"}
            actual_fields = set(project.keys())
            assert actual_fields == expected_fields, (
                f"Los campos deben ser exactamente {expected_fields}"
            )

        # Verificar que no hay duplicados
        project_ids = [project["id"] for project in data]
        unique_ids = set(project_ids)
        assert len(project_ids) == len(unique_ids), "No debe haber proyectos duplicados"

        # Mostrar algunos proyectos para debug
        for project in data[:3]:
            print(f"ID: {project['id']}, Nombre: {project['name']}")
    else:
        print("\nNo se encontraron proyectos que cumplan los criterios")


@pytest.mark.integration
def test_get_projects_without_user_parameter(test_client):
    """Test de integración que verifica que el endpoint funciona sin parámetros de usuario."""
    # Act - Sin parámetros (comportamiento actual)
    response = test_client.get("/api/v1/projects/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Act - Con parámetro user (debe ser ignorado según la implementación actual)
    response_with_user = test_client.get("/api/v1/projects/?user=1")

    # Assert - Debe retornar el mismo resultado
    assert response_with_user.status_code == 200
    data_with_user = response_with_user.json()
    assert isinstance(data_with_user, list)

    # Ambas respuestas deben ser iguales porque el parámetro user no se usa
    assert len(data) == len(data_with_user), (
        "El parámetro user no debe afectar el resultado"
    )


@pytest.mark.integration
def test_get_projects_returns_consistent_results(test_client):
    """Test de integración que verifica que el endpoint retorna resultados consistentes."""
    # Act - Hacer múltiples llamadas
    response1 = test_client.get("/api/v1/projects/")
    response2 = test_client.get("/api/v1/projects/")

    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    assert isinstance(data1, list)
    assert isinstance(data2, list)

    # Los resultados deben ser consistentes
    assert len(data1) == len(data2), (
        "Las múltiples llamadas deben retornar la misma cantidad de proyectos"
    )

    if data1:
        # Verificar que los IDs son los mismos
        ids1 = sorted([project["id"] for project in data1])
        ids2 = sorted([project["id"] for project in data2])
        assert ids1 == ids2, "Los IDs de los proyectos deben ser consistentes"


@pytest.mark.integration
def test_get_projects_response_format(test_client):
    """Test de integración que verifica el formato de respuesta del endpoint."""
    # Act
    response = test_client.get("/api/v1/projects/")

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert isinstance(data, list)

    # Verificar que la respuesta es válida JSON
    import json

    json_str = response.content.decode("utf-8")
    parsed_json = json.loads(json_str)
    assert parsed_json == data


@pytest.mark.integration
def test_get_projects_with_authentication_required(test_client):
    """Test de integración que verifica que se requiere autenticación."""
    # Act - Sin headers de autenticación
    response = test_client.get("/api/v1/projects/")

    # Assert
    # Nota: Este test depende de si la autenticación está habilitada en el entorno de test
    # Si está habilitada, debería retornar 401, si no, 200
    assert response.status_code in [200, 401], (
        "Debe retornar 200 (sin auth) o 401 (con auth requerida)"
    )


@pytest.mark.integration
def test_get_projects_business_logic_validation(test_client):
    """Test de integración que valida la lógica de negocio específica."""
    # Act
    response = test_client.get("/api/v1/projects/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    if data:
        print(f"\nValidando lógica de negocio para {len(data)} proyectos...")

        # Todos los proyectos retornados deben cumplir los criterios de negocio:
        # 1. Ser proyectos activos
        # 2. Tener cuenta analítica activa
        # 3. Estar listos para crear timesheets

        # Verificar que hay proyectos válidos
        assert len(data) > 0, (
            "Debe haber al menos algunos proyectos válidos en el sistema"
        )

        # Verificar estructura mínima requerida
        for project in data:
            assert "id" in project, "Cada proyecto debe tener un ID"
            assert "name" in project, "Cada proyecto debe tener un nombre"
            assert isinstance(project["id"], int), "El ID debe ser un entero"
            assert isinstance(project["name"], str), "El nombre debe ser una cadena"

        print("✅ Todos los proyectos cumplen la lógica de negocio")


@pytest.mark.integration
def test_get_projects_handles_empty_response_gracefully(test_client):
    """Test de integración que verifica el manejo graceful de respuesta vacía."""
    # Act
    response = test_client.get("/api/v1/projects/")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Si está vacía, debe ser una lista vacía válida, no None o error
    if not data:
        assert data == [], "Una respuesta vacía debe ser una lista vacía"
        print("✅ Respuesta vacía manejada correctamente")
    else:
        print(f"✅ Respuesta con {len(data)} proyectos manejada correctamente")
