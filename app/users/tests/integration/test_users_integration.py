import pytest
from fastapi.testclient import TestClient
from app.main import app  # Asegúrate de importar tu app de FastAPI


@pytest.mark.integration
def test_sync_users_response_structure(test_client: TestClient):
    """Test de integración que prueba la estructura de la respuesta de /users/sync."""
    response = test_client.post("/api/v1/users/sync")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data
    assert "users_created" in data
    assert "users_updated" in data
    assert "total_processed" in data
    assert data["success"] is True


@pytest.mark.integration
def test_sync_users_functional(test_client: TestClient, local_db_session):
    """Test de integración que verifica la funcionalidad de la sincronización."""
    # Asegurar que la tabla de usuarios esté vacía para un test limpio
    from app.users.infra.db.models import UserModel

    local_db_session.query(UserModel).delete()
    local_db_session.commit()

    # Primera sincronización
    response1 = test_client.post("/api/v1/users/sync")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["users_created"] > 0
    assert data1["users_updated"] == 0

    # Segunda sincronización (no debería haber cambios)
    response2 = test_client.post("/api/v1/users/sync")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["users_created"] == 0
    assert data2["users_updated"] == 0
    assert data2["total_processed"] == data1["total_processed"]
