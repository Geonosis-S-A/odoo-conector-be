import pytest
from app.users.infra.db.models import UserModel


@pytest.mark.integration
def test_sync_user_changes_endpoint_success(test_client):
    """Test de integración que prueba la sincronización de cambios de usuarios desde Odoo."""
    response = test_client.post("/api/v1/users/sync-changes")
    print(response.text)
    assert response.status_code == 200
    data = response.json()
    
    # Verificar la estructura de la respuesta
    assert "updated" in data
    assert "unchanged" in data
    assert "summary" in data
    
    assert isinstance(data["updated"], list)
    assert isinstance(data["unchanged"], list)
    assert isinstance(data["summary"], str)
    
    # Verificar que el summary contiene información esperada
    assert "Actualizados:" in data["summary"]
    assert "Sin cambios:" in data["summary"]


@pytest.mark.integration
def test_sync_user_changes_with_existing_users(test_client, local_db_session):
    """Test de integración que verifica la sincronización cuando hay usuarios existentes."""
    # Primero sincronizar usuarios para tener datos base
    sync_response = test_client.post("/api/v1/users/sync")
    assert sync_response.status_code == 200
    initial_users = sync_response.json()
    
    # Modificar algunos usuarios en la base de datos local para simular diferencias
    if len(initial_users) > 0:
        user_to_modify = initial_users[0]
        user_model = (
            local_db_session.query(UserModel)
            .filter(UserModel.id == user_to_modify["id"])
            .first()
        )
        if user_model:
            # Cambiar el email y nombre para que sea diferente de Odoo
            user_model.email = "modified_email@test.com"
            user_model.full_name = "Modified Name"
            user_model.is_active = True
            user_model.is_superuser = True
            local_db_session.commit()
    
    # Ejecutar sync-changes
    response = test_client.post("/api/v1/users/sync-changes")
    assert response.status_code == 200
    data = response.json()
    
    # Verificar que hay usuarios actualizados o sin cambios
    total_users = len(data["updated"]) + len(data["unchanged"])
    assert total_users > 0
    
    # Verificar estructura de usuarios en la respuesta
    for user_list in [data["updated"], data["unchanged"]]:
        for user in user_list:
            assert "id" in user
            assert "email" in user
            assert "full_name" in user
            assert "is_active" in user
            assert "is_superuser" in user
            assert isinstance(user["id"], int)
            assert isinstance(user["email"], str)
            assert isinstance(user["full_name"], str)
            assert isinstance(user["is_active"], bool)
            assert isinstance(user["is_superuser"], bool)


@pytest.mark.integration
def test_sync_user_changes_preserves_user_state(test_client, local_db_session):
    """Test que verifica que el estado del usuario (is_active, is_superuser) se preserve."""
    # Primero sincronizar usuarios
    sync_response = test_client.post("/api/v1/users/sync")
    assert sync_response.status_code == 200
    initial_users = sync_response.json()
    
    if len(initial_users) > 0:
        # Activar y dar permisos de superuser a algunos usuarios
        for i, user in enumerate(initial_users[:2]):  # Modificar los primeros 2
            user_model = (
                local_db_session.query(UserModel)
                .filter(UserModel.id == user["id"])
                .first()
            )
            if user_model:
                user_model.is_active = True
                user_model.is_superuser = True
        local_db_session.commit()
        
        # Ejecutar sync-changes
        response = test_client.post("/api/v1/users/sync-changes")
        assert response.status_code == 200
        data = response.json()
        
        # Verificar que los usuarios mantienen su estado
        all_users = data["updated"] + data["unchanged"]
        modified_user_ids = [user["id"] for user in initial_users[:2]]
        
        for user in all_users:
            if user["id"] in modified_user_ids:
                # Estos usuarios deben mantener is_active=True e is_superuser=True
                assert user["is_active"] is True
                assert user["is_superuser"] is True


@pytest.mark.integration
def test_sync_user_changes_only_updates_existing_users(test_client, local_db_session):
    """Test que verifica que solo se actualicen usuarios existentes, no se creen nuevos."""
    # Obtener el número inicial de usuarios
    initial_sync = test_client.post("/api/v1/users/sync")
    assert initial_sync.status_code == 200
    initial_count = len(initial_sync.json())
    
    # Ejecutar sync-changes
    response = test_client.post("/api/v1/users/sync-changes")
    assert response.status_code == 200
    data = response.json()
    
    # Verificar que el número total de usuarios no cambió
    total_processed = len(data["updated"]) + len(data["unchanged"])
    assert total_processed == initial_count
    
    # Verificar en la base de datos que no se crearon usuarios nuevos
    final_sync = test_client.post("/api/v1/users/sync")
    assert final_sync.status_code == 200
    final_count = len(final_sync.json())
    
    assert final_count == initial_count


@pytest.mark.integration
def test_sync_user_changes_updates_email_and_name_from_odoo(test_client, local_db_session):
    """Test que verifica que los cambios de email y nombre se sincronicen desde Odoo."""
    # Primero sincronizar usuarios
    sync_response = test_client.post("/api/v1/users/sync")
    assert sync_response.status_code == 200
    initial_users = sync_response.json()
    
    if len(initial_users) > 0:
        user_to_test = initial_users[0]
        original_email = user_to_test["email"]
        original_name = user_to_test["full_name"]
        
        # Modificar el usuario en la base de datos local
        user_model = (
            local_db_session.query(UserModel)
            .filter(UserModel.id == user_to_test["id"])
            .first()
        )
        if user_model:
            user_model.email = "different@test.com"
            user_model.full_name = "Different Name"
            user_model.is_active = True
            user_model.is_superuser = True
            local_db_session.commit()
            
            # Ejecutar sync-changes
            response = test_client.post("/api/v1/users/sync-changes")
            assert response.status_code == 200
            data = response.json()
            
            # Buscar el usuario actualizado
            updated_user = None
            for user in data["updated"]:
                if user["id"] == user_to_test["id"]:
                    updated_user = user
                    break
            
            if updated_user:
                # Verificar que el email y nombre se actualizaron desde Odoo
                assert updated_user["email"] == original_email
                assert updated_user["full_name"] == original_name
                # Verificar que el estado se mantuvo
                assert updated_user["is_active"] is True
                assert updated_user["is_superuser"] is True


@pytest.mark.integration
def test_sync_user_changes_handles_no_changes_scenario(test_client):
    """Test que verifica el manejo cuando no hay cambios que sincronizar."""
    # Ejecutar sync dos veces seguidas
    first_response = test_client.post("/api/v1/users/sync-changes")
    assert first_response.status_code == 200
    
    second_response = test_client.post("/api/v1/users/sync-changes")
    assert second_response.status_code == 200
    
    data = second_response.json()
    
    # En la segunda ejecución, todos los usuarios deberían estar sin cambios
    assert len(data["updated"]) == 0
    assert len(data["unchanged"]) >= 0  # Puede ser 0 si no hay usuarios
    
    # Verificar que el summary refleje esto
    assert "Actualizados: 0" in data["summary"]


@pytest.mark.integration
def test_sync_user_changes_response_structure(test_client):
    """Test que verifica la estructura completa de la respuesta del endpoint."""
    response = test_client.post("/api/v1/users/sync-changes")
    assert response.status_code == 200
    data = response.json()
    
    # Verificar estructura principal
    required_keys = ["updated", "unchanged", "summary"]
    for key in required_keys:
        assert key in data
    
    # Verificar que updated y unchanged son listas
    assert isinstance(data["updated"], list)
    assert isinstance(data["unchanged"], list)
    assert isinstance(data["summary"], str)
    
    # Verificar estructura de cada usuario en las listas
    for user_list_name in ["updated", "unchanged"]:
        for user in data[user_list_name]:
            required_user_keys = ["id", "email", "full_name", "is_active", "is_superuser"]
            for key in required_user_keys:
                assert key in user
            
            # Verificar tipos de datos
            assert isinstance(user["id"], int)
            assert isinstance(user["email"], str)
            assert isinstance(user["full_name"], str)
            assert isinstance(user["is_active"], bool)
            assert isinstance(user["is_superuser"], bool)
            
            # Verificar que el email tiene formato válido básico
            assert "@" in user["email"]
            assert len(user["full_name"]) > 0


@pytest.mark.integration
def test_sync_user_changes_error_handling():
    """Test que verifica el manejo de errores del endpoint."""
    # TODO: Implementar test con mock de error de conexión con Odoo
    # Este test requeriría mockear la conexión de Odoo para simular errores
    pass 