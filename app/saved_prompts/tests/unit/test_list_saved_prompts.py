import pytest
from unittest.mock import Mock
from datetime import datetime

from app.saved_prompts.application.use_cases.list_saved_prompts import (
    ListSavedPromptsUseCase,
)
from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository


class TestListSavedPromptsUseCase:
    @pytest.fixture
    def mock_repository(self):
        """Fixture que proporciona un repositorio mockeado."""
        return Mock(spec=SavedPromptRepository)

    @pytest.fixture
    def use_case(self, mock_repository):
        """Fixture que proporciona el caso de uso con el repositorio mockeado."""
        return ListSavedPromptsUseCase(mock_repository)

    def test_execute_returns_all_prompts_for_user(self, use_case, mock_repository):
        """Test que verifica que retorna todos los prompts de un usuario."""
        # Arrange
        user_id = 617
        test_prompts = [
            SavedPrompt(
                id=1,
                user_id=user_id,
                prompt_text="cargame 8 horas en SX1",
                created_at=datetime(2024, 11, 25, 10, 0, 0),
            ),
            SavedPrompt(
                id=2,
                user_id=user_id,
                prompt_text="cargar 4 horas en proyecto ABC",
                created_at=datetime(2024, 11, 24, 15, 0, 0),
            ),
            SavedPrompt(
                id=3,
                user_id=user_id,
                prompt_text="timesheet de la semana",
                created_at=datetime(2024, 11, 23, 9, 0, 0),
            ),
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        result = use_case.execute(user_id)

        # Assert
        mock_repository.list_by_user.assert_called_once_with(user_id)
        assert len(result) == 3
        assert all(isinstance(prompt, SavedPrompt) for prompt in result)
        assert result[0].id == 1
        assert result[0].prompt_text == "cargame 8 horas en SX1"
        assert result[1].id == 2
        assert result[1].prompt_text == "cargar 4 horas en proyecto ABC"
        assert result[2].id == 3
        assert result[2].prompt_text == "timesheet de la semana"

    def test_execute_returns_empty_list_when_no_prompts(
        self, use_case, mock_repository
    ):
        """Test que verifica que retorna lista vacía cuando no hay prompts."""
        # Arrange
        user_id = 617
        mock_repository.list_by_user.return_value = []

        # Act
        result = use_case.execute(user_id)

        # Assert
        mock_repository.list_by_user.assert_called_once_with(user_id)
        assert result == []
        assert len(result) == 0
        assert isinstance(result, list)

    def test_execute_with_different_user_ids(self, use_case, mock_repository):
        """Test que verifica que se llama al repositorio con el user_id correcto."""
        # Arrange
        user_id = 999
        test_prompts = [
            SavedPrompt(
                id=10,
                user_id=user_id,
                prompt_text="test prompt",
                created_at=datetime.now(),
            )
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        result = use_case.execute(user_id)

        # Assert
        mock_repository.list_by_user.assert_called_once_with(999)
        assert len(result) == 1
        assert result[0].user_id == user_id

    def test_execute_preserves_prompt_properties(self, use_case, mock_repository):
        """Test que verifica que se preservan todas las propiedades de los prompts."""
        # Arrange
        user_id = 617
        created_at = datetime(2024, 11, 25, 14, 30, 45)
        test_prompts = [
            SavedPrompt(
                id=42,
                user_id=user_id,
                prompt_text="Prompt con caracteres especiales: áéíóú ñ @#$",
                created_at=created_at,
            )
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 1
        assert result[0].id == 42
        assert result[0].user_id == user_id
        assert result[0].prompt_text == "Prompt con caracteres especiales: áéíóú ñ @#$"
        assert result[0].created_at == created_at

    def test_execute_returns_prompts_in_order_from_repository(
        self, use_case, mock_repository
    ):
        """Test que verifica que retorna los prompts en el orden del repositorio."""
        # Arrange
        user_id = 617
        # El repositorio devuelve ordenados por fecha descendente (más recientes primero)
        test_prompts = [
            SavedPrompt(
                id=3,
                user_id=user_id,
                prompt_text="prompt más reciente",
                created_at=datetime(2024, 11, 25, 10, 0, 0),
            ),
            SavedPrompt(
                id=2,
                user_id=user_id,
                prompt_text="prompt intermedio",
                created_at=datetime(2024, 11, 24, 10, 0, 0),
            ),
            SavedPrompt(
                id=1,
                user_id=user_id,
                prompt_text="prompt más antiguo",
                created_at=datetime(2024, 11, 23, 10, 0, 0),
            ),
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 3
        # Verificar que mantiene el orden del repositorio
        assert result[0].id == 3
        assert result[1].id == 2
        assert result[2].id == 1
        assert result[0].created_at > result[1].created_at > result[2].created_at

    def test_execute_with_single_prompt(self, use_case, mock_repository):
        """Test que verifica que maneja correctamente un solo prompt."""
        # Arrange
        user_id = 617
        test_prompts = [
            SavedPrompt(
                id=1,
                user_id=user_id,
                prompt_text="único prompt",
                created_at=datetime.now(),
            )
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        result = use_case.execute(user_id)

        # Assert
        mock_repository.list_by_user.assert_called_once_with(user_id)
        assert len(result) == 1
        assert isinstance(result[0], SavedPrompt)
        assert result[0].id == 1
        assert result[0].prompt_text == "único prompt"

    def test_execute_repository_exception_propagation(self, use_case, mock_repository):
        """Test que verifica que las excepciones del repositorio se propagan."""
        # Arrange
        user_id = 617
        mock_repository.list_by_user.side_effect = Exception(
            "Database connection failed"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(user_id)

        assert "Database connection failed" in str(exc_info.value)
        mock_repository.list_by_user.assert_called_once_with(user_id)

    def test_execute_calls_repository_only_once(self, use_case, mock_repository):
        """Test que verifica que solo se llama al repositorio una vez."""
        # Arrange
        user_id = 617
        mock_repository.list_by_user.return_value = []

        # Act
        use_case.execute(user_id)

        # Assert
        assert mock_repository.list_by_user.call_count == 1
        mock_repository.list_by_user.assert_called_once_with(user_id)

    def test_execute_with_many_prompts(self, use_case, mock_repository):
        """Test que verifica el manejo de muchos prompts."""
        # Arrange
        user_id = 617
        test_prompts = [
            SavedPrompt(
                id=i,
                user_id=user_id,
                prompt_text=f"prompt {i}",
                created_at=datetime(
                    2024, 11, i % 28 + 1, 10, i % 60, 0
                ),  # Fechas válidas
            )
            for i in range(1, 101)  # 100 prompts
        ]
        mock_repository.list_by_user.return_value = test_prompts

        # Act
        result = use_case.execute(user_id)

        # Assert
        assert len(result) == 100
        assert all(isinstance(prompt, SavedPrompt) for prompt in result)
        mock_repository.list_by_user.assert_called_once_with(user_id)
