import pytest
from unittest.mock import Mock
from datetime import datetime

from app.saved_prompts.api.routers import get_saved_prompt_repository
from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository


@pytest.fixture
def mock_repository():
    """Fixture que proporciona un repositorio mockeado."""
    return Mock(spec=SavedPromptRepository)


@pytest.fixture
def override_saved_prompt_repository(mock_repository):
    """Fixture para sobrescribir la dependencia del repositorio."""

    def _override():
        return mock_repository

    return _override


@pytest.fixture(autouse=True)
def configure_test_client(test_client, override_saved_prompt_repository):
    """Configura el test client con las dependencias mockeadas."""
    test_client.app.dependency_overrides[get_saved_prompt_repository] = (
        override_saved_prompt_repository
    )


class TestCreateSavedPrompt:
    def test_create_saved_prompt_success(self, mock_repository, test_client):
        """Test que verifica la creación exitosa de un prompt guardado."""
        # Arrange
        created_prompt = SavedPrompt(
            id=1,
            user_id=1,  # Del override_get_current_user
            prompt_text="cargame 8 horas en SX1 para hoy",
            created_at=datetime(2024, 11, 25, 10, 30, 0),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.post(
            "/api/v1/saved-prompts/",
            headers=headers,
            json={"prompt_text": "cargame 8 horas en SX1 para hoy"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["user_id"] == 1
        assert data["prompt_text"] == "cargame 8 horas en SX1 para hoy"
        assert "created_at" in data
        mock_repository.create.assert_called_once()

    def test_create_saved_prompt_empty_text_returns_422(
        self, mock_repository, test_client
    ):
        """Test que verifica que texto vacío retorna error 422 (validación de Pydantic)."""
        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.post(
            "/api/v1/saved-prompts/",
            headers=headers,
            json={"prompt_text": ""},
        )

        # Assert
        # Pydantic valida min_length=1, por lo que retorna 422
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_saved_prompt_with_long_text(self, mock_repository, test_client):
        """Test que verifica la creación con texto largo."""
        # Arrange
        long_text = "a" * 1000
        created_prompt = SavedPrompt(
            id=1,
            user_id=1,
            prompt_text=long_text,
            created_at=datetime.now(),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.post(
            "/api/v1/saved-prompts/",
            headers=headers,
            json={"prompt_text": long_text},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert len(data["prompt_text"]) == 1000

    def test_create_saved_prompt_with_special_characters(
        self, mock_repository, test_client
    ):
        """Test que verifica la creación con caracteres especiales."""
        # Arrange
        prompt_text = "cargame 8hs en 'SX-1' con: áéíóú ñ @#$%"
        created_prompt = SavedPrompt(
            id=1,
            user_id=1,
            prompt_text=prompt_text,
            created_at=datetime.now(),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.post(
            "/api/v1/saved-prompts/",
            headers=headers,
            json={"prompt_text": prompt_text},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["prompt_text"] == prompt_text

    def test_create_saved_prompt_response_format(self, mock_repository, test_client):
        """Test que verifica el formato de respuesta del endpoint."""
        # Arrange
        created_prompt = SavedPrompt(
            id=42,
            user_id=1,
            prompt_text="test prompt",
            created_at=datetime(2024, 11, 25, 14, 30, 0),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.post(
            "/api/v1/saved-prompts/",
            headers=headers,
            json={"prompt_text": "test prompt"},
        )

        # Assert
        assert response.status_code == 201
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert set(data.keys()) == {"id", "user_id", "prompt_text", "created_at"}

    def test_create_saved_prompt_repository_error_returns_500(
        self, mock_repository, test_client
    ):
        """Test que verifica que errores del repositorio retornan 500."""
        # Arrange
        mock_repository.create.side_effect = Exception("Database connection failed")

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.post(
            "/api/v1/saved-prompts/",
            headers=headers,
            json={"prompt_text": "test prompt"},
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"].lower() or "Error" in data["detail"]


class TestListSavedPrompts:
    def test_list_saved_prompts_success(self, mock_repository, test_client):
        """Test que verifica el listado exitoso de prompts guardados."""
        # Arrange
        test_prompts = [
            SavedPrompt(
                id=1,
                user_id=1,
                prompt_text="cargame 8 horas en SX1",
                created_at=datetime(2024, 11, 25, 10, 0, 0),
            ),
            SavedPrompt(
                id=2,
                user_id=1,
                prompt_text="cargar 4 horas en ABC",
                created_at=datetime(2024, 11, 24, 15, 0, 0),
            ),
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/saved-prompts/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["prompt_text"] == "cargame 8 horas en SX1"
        assert data[1]["id"] == 2
        assert data[1]["prompt_text"] == "cargar 4 horas en ABC"
        mock_repository.list_by_user.assert_called_once_with(1)

    def test_list_saved_prompts_empty_returns_empty_array(
        self, mock_repository, test_client
    ):
        """Test que verifica que retorna array vacío cuando no hay prompts."""
        # Arrange
        mock_repository.list_by_user.return_value = []

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/saved-prompts/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert len(data) == 0
        assert isinstance(data, list)
        mock_repository.list_by_user.assert_called_once_with(1)

    def test_list_saved_prompts_response_format(self, mock_repository, test_client):
        """Test que verifica el formato de respuesta del endpoint."""
        # Arrange
        test_prompts = [
            SavedPrompt(
                id=1,
                user_id=1,
                prompt_text="test prompt",
                created_at=datetime(2024, 11, 25, 10, 0, 0),
            )
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/saved-prompts/", headers=headers)

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        prompt = data[0]
        assert set(prompt.keys()) == {"id", "user_id", "prompt_text", "created_at"}

    def test_list_saved_prompts_preserves_order(self, mock_repository, test_client):
        """Test que verifica que se preserva el orden de los prompts."""
        # Arrange
        test_prompts = [
            SavedPrompt(
                id=3,
                user_id=1,
                prompt_text="más reciente",
                created_at=datetime(2024, 11, 25, 10, 0, 0),
            ),
            SavedPrompt(
                id=2,
                user_id=1,
                prompt_text="intermedio",
                created_at=datetime(2024, 11, 24, 10, 0, 0),
            ),
            SavedPrompt(
                id=1,
                user_id=1,
                prompt_text="más antiguo",
                created_at=datetime(2024, 11, 23, 10, 0, 0),
            ),
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/saved-prompts/", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["id"] == 3
        assert data[1]["id"] == 2
        assert data[2]["id"] == 1

    def test_list_saved_prompts_repository_error_returns_500(
        self, mock_repository, test_client
    ):
        """Test que verifica que errores del repositorio retornan 500."""
        # Arrange
        mock_repository.list_by_user.side_effect = Exception(
            "Database connection failed"
        )

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.get("/api/v1/saved-prompts/", headers=headers)

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestDeleteSavedPrompt:
    def test_delete_saved_prompt_success(self, mock_repository, test_client):
        """Test que verifica la eliminación exitosa de un prompt."""
        # Arrange
        prompt_id = 1
        mock_repository.delete.return_value = True

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.delete(
            f"/api/v1/saved-prompts/{prompt_id}", headers=headers
        )

        # Assert
        assert response.status_code == 204
        mock_repository.delete.assert_called_once_with(prompt_id, 1)

    def test_delete_saved_prompt_not_found_returns_404(
        self, mock_repository, test_client
    ):
        """Test que verifica que prompt inexistente retorna 404."""
        # Arrange
        prompt_id = 999
        mock_repository.delete.side_effect = ValueError(
            f"Prompt con ID {prompt_id} no existe o no pertenece al usuario"
        )

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.delete(
            f"/api/v1/saved-prompts/{prompt_id}", headers=headers
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "no existe o no pertenece al usuario" in data["detail"]

    def test_delete_saved_prompt_from_different_user_returns_404(
        self, mock_repository, test_client
    ):
        """Test que verifica que no se puede eliminar prompt de otro usuario."""
        # Arrange
        prompt_id = 1
        mock_repository.delete.side_effect = ValueError(
            f"Prompt con ID {prompt_id} no existe o no pertenece al usuario"
        )

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.delete(
            f"/api/v1/saved-prompts/{prompt_id}", headers=headers
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_delete_saved_prompt_with_different_ids(self, mock_repository, test_client):
        """Test que verifica la eliminación con diferentes IDs."""
        # Arrange
        prompt_id = 42
        mock_repository.delete.return_value = True

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.delete(
            f"/api/v1/saved-prompts/{prompt_id}", headers=headers
        )

        # Assert
        assert response.status_code == 204
        mock_repository.delete.assert_called_once_with(42, 1)

    def test_delete_saved_prompt_repository_error_returns_500(
        self, mock_repository, test_client
    ):
        """Test que verifica que errores del repositorio retornan 500."""
        # Arrange
        prompt_id = 1
        mock_repository.delete.side_effect = Exception("Database connection failed")

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.delete(
            f"/api/v1/saved-prompts/{prompt_id}", headers=headers
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_delete_saved_prompt_no_content_response(
        self, mock_repository, test_client
    ):
        """Test que verifica que la respuesta es 204 No Content sin body."""
        # Arrange
        prompt_id = 1
        mock_repository.delete.return_value = True

        # Act
        headers = {"Authorization": "Bearer testtoken"}
        response = test_client.delete(
            f"/api/v1/saved-prompts/{prompt_id}", headers=headers
        )

        # Assert
        assert response.status_code == 204
        assert response.text == ""  # No content
