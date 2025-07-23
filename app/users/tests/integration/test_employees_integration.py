import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_get_all_employees_response_structure(test_client: TestClient):
    """Test de integración que prueba la estructura de la respuesta de /users/employees."""
    response = test_client.get("/api/v1/users/employees")
    assert response.status_code == 200
    data = response.json()

    # Verificar estructura de la respuesta
    assert "success" in data
    assert "message" in data
    assert "employees" in data
    assert "total_employees" in data
    assert data["success"] is True

    # Verificar que employees es una lista
    assert isinstance(data["employees"], list)
    assert isinstance(data["total_employees"], int)

    # Si hay empleados, verificar estructura de cada empleado
    if data["employees"]:
        for employee in data["employees"]:
            assert "id" in employee
            assert "email" in employee
            assert "full_name" in employee
            assert isinstance(employee["id"], int)
            assert isinstance(employee["email"], str)
            assert isinstance(employee["full_name"], str)


@pytest.mark.integration
def test_get_all_employees_functional(test_client: TestClient):
    """Test de integración que verifica la funcionalidad del endpoint de empleados."""
    # Llamar al endpoint
    response = test_client.get("/api/v1/users/employees")
    assert response.status_code == 200

    data = response.json()

    # Verificar que la respuesta es exitosa
    assert data["success"] is True
    assert "empleados obtenidos exitosamente" in data["message"].lower()

    # Verificar consistencia entre la lista y el contador
    assert data["total_employees"] == len(data["employees"])
