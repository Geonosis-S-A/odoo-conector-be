import pytest
from unittest.mock import Mock

from app.saved_prompts.application.use_cases.delete_saved_prompt import (
    DeleteSavedPromptUseCase,
)
from app.saved_prompts.domain.repositories import SavedPromptRepository


class TestDeleteSavedPromptUseCase:
    @pytest.fixture
    def mock_repository(self):
        """Fixture que proporciona un repositorio mockeado."""
        return Mock(spec=SavedPromptRepository)

    @pytest.fixture
    def use_case(self, mock_repository):
        """Fixture que proporciona el caso de uso con el repositorio mockeado."""
        return DeleteSavedPromptUseCase(mock_repository)

    def test_execute_deletes_prompt_successfully(self, use_case, mock_repository):
        """Test que verifica la eliminación exitosa de un prompt."""
        # Arrange
        prompt_id = 1
        user_id = 617
        mock_repository.delete.return_value = True

        # Act
        result = use_case.execute(prompt_id, user_id)

        # Assert
        assert result is True
        mock_repository.delete.assert_called_once_with(prompt_id, user_id)

    def test_execute_raises_value_error_when_prompt_not_found(
        self, use_case, mock_repository
    ):
        """Test que verifica que se lanza error cuando el prompt no existe."""
        # Arrange
        prompt_id = 999
        user_id = 617
        mock_repository.delete.side_effect = ValueError(
            f"Prompt con ID {prompt_id} no existe o no pertenece al usuario"
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(prompt_id, user_id)

        assert "no existe o no pertenece al usuario" in str(exc_info.value)
        mock_repository.delete.assert_called_once_with(prompt_id, user_id)

    def test_execute_raises_value_error_when_prompt_belongs_to_different_user(
        self, use_case, mock_repository
    ):
        """Test que verifica que no se puede eliminar prompt de otro usuario."""
        # Arrange
        prompt_id = 1
        user_id = 617
        mock_repository.delete.side_effect = ValueError(
            f"Prompt con ID {prompt_id} no existe o no pertenece al usuario"
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(prompt_id, user_id)

        assert "no pertenece al usuario" in str(exc_info.value)
        mock_repository.delete.assert_called_once_with(prompt_id, user_id)

    def test_execute_with_different_prompt_ids(self, use_case, mock_repository):
        """Test que verifica la eliminación con diferentes IDs de prompt."""
        # Arrange
        prompt_id = 42
        user_id = 617
        mock_repository.delete.return_value = True

        # Act
        result = use_case.execute(prompt_id, user_id)

        # Assert
        assert result is True
        mock_repository.delete.assert_called_once_with(42, user_id)

    def test_execute_with_different_user_ids(self, use_case, mock_repository):
        """Test que verifica la eliminación con diferentes IDs de usuario."""
        # Arrange
        prompt_id = 1
        user_id = 999
        mock_repository.delete.return_value = True

        # Act
        result = use_case.execute(prompt_id, user_id)

        # Assert
        assert result is True
        mock_repository.delete.assert_called_once_with(prompt_id, 999)

    def test_execute_repository_exception_propagation(self, use_case, mock_repository):
        """Test que verifica que las excepciones del repositorio se propagan."""
        # Arrange
        prompt_id = 1
        user_id = 617
        mock_repository.delete.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(prompt_id, user_id)

        assert "Database connection failed" in str(exc_info.value)
        mock_repository.delete.assert_called_once_with(prompt_id, user_id)

    def test_execute_calls_repository_delete_with_correct_parameters(
        self, use_case, mock_repository
    ):
        """Test que verifica que se llama al repositorio con los parámetros correctos."""
        # Arrange
        prompt_id = 123
        user_id = 456
        mock_repository.delete.return_value = True

        # Act
        use_case.execute(prompt_id, user_id)

        # Assert
        mock_repository.delete.assert_called_once()
        # Verificar los argumentos exactos de la llamada
        call_args = mock_repository.delete.call_args
        assert call_args[0][0] == prompt_id  # Primer argumento
        assert call_args[0][1] == user_id  # Segundo argumento

    def test_execute_calls_repository_only_once(self, use_case, mock_repository):
        """Test que verifica que solo se llama al repositorio una vez."""
        # Arrange
        prompt_id = 1
        user_id = 617
        mock_repository.delete.return_value = True

        # Act
        use_case.execute(prompt_id, user_id)

        # Assert
        assert mock_repository.delete.call_count == 1
        mock_repository.delete.assert_called_once_with(prompt_id, user_id)

    def test_execute_returns_true_on_successful_deletion(
        self, use_case, mock_repository
    ):
        """Test que verifica que retorna True cuando la eliminación es exitosa."""
        # Arrange
        prompt_id = 1
        user_id = 617
        mock_repository.delete.return_value = True

        # Act
        result = use_case.execute(prompt_id, user_id)

        # Assert
        assert result is True
        assert isinstance(result, bool)
