import pytest
from unittest.mock import Mock
from datetime import datetime

from app.saved_prompts.application.use_cases.update_saved_prompt import (
    UpdateSavedPromptUseCase,
)
from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository


class TestUpdateSavedPromptUseCase:
    @pytest.fixture
    def mock_repository(self):
        """Fixture que proporciona un repositorio mockeado."""
        return Mock(spec=SavedPromptRepository)

    @pytest.fixture
    def use_case(self, mock_repository):
        """Fixture que proporciona el caso de uso con el repositorio mockeado."""
        return UpdateSavedPromptUseCase(mock_repository)

    @pytest.fixture
    def existing_prompt(self):
        """Fixture que proporciona un prompt existente."""
        return SavedPrompt(
            id=1,
            user_id=617,
            prompt_text="texto original del prompt",
            created_at=datetime(2024, 11, 25, 10, 0, 0),
        )

    @pytest.fixture
    def updated_prompt(self):
        """Fixture que proporciona un prompt actualizado."""
        return SavedPrompt(
            id=1,
            user_id=617,
            prompt_text="texto actualizado del prompt",
            created_at=datetime(2024, 11, 25, 10, 0, 0),
        )

    def test_execute_updates_prompt_successfully(
        self, use_case, mock_repository, existing_prompt, updated_prompt
    ):
        """Test que verifica la actualización exitosa de un prompt."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "texto actualizado del prompt"
        mock_repository.get_by_id.return_value = existing_prompt
        mock_repository.update.return_value = updated_prompt

        # Act
        result = use_case.execute(prompt_id, user_id, new_text)

        # Assert
        assert result == updated_prompt
        mock_repository.get_by_id.assert_called_once_with(prompt_id)
        mock_repository.update.assert_called_once()
        updated_arg = mock_repository.update.call_args[0][0]
        assert updated_arg.prompt_text == new_text

    def test_execute_trims_whitespace_from_new_text(
        self, use_case, mock_repository, existing_prompt, updated_prompt
    ):
        """Test que verifica que se eliminan espacios en blanco del nuevo texto."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "  texto actualizado del prompt  "
        mock_repository.get_by_id.return_value = existing_prompt
        mock_repository.update.return_value = updated_prompt

        # Act
        result = use_case.execute(prompt_id, user_id, new_text)

        # Assert
        mock_repository.update.assert_called_once()
        updated_arg = mock_repository.update.call_args[0][0]
        assert updated_arg.prompt_text == new_text.strip()
        assert not updated_arg.prompt_text.startswith(" ")
        assert not updated_arg.prompt_text.endswith(" ")

    def test_execute_raises_value_error_for_empty_text(
        self, use_case, mock_repository, existing_prompt
    ):
        """Test que verifica que no se puede actualizar con texto vacío."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = ""
        mock_repository.get_by_id.return_value = existing_prompt

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(prompt_id, user_id, new_text)

        assert "El texto del prompt no puede estar vacío" in str(exc_info.value)
        mock_repository.get_by_id.assert_not_called()
        mock_repository.update.assert_not_called()

    def test_execute_raises_value_error_for_whitespace_only_text(
        self, use_case, mock_repository, existing_prompt
    ):
        """Test que verifica que no se puede actualizar con solo espacios."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "   "
        mock_repository.get_by_id.return_value = existing_prompt

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(prompt_id, user_id, new_text)

        assert "El texto del prompt no puede estar vacío" in str(exc_info.value)

    def test_execute_raises_value_error_when_prompt_not_found(
        self, use_case, mock_repository
    ):
        """Test que verifica que se lanza error cuando el prompt no existe."""
        # Arrange
        prompt_id = 999
        user_id = 617
        new_text = "nuevo texto"
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(prompt_id, user_id, new_text)

        assert f"Prompt con ID {prompt_id} no existe" in str(exc_info.value)
        mock_repository.get_by_id.assert_called_once_with(prompt_id)
        mock_repository.update.assert_not_called()

    def test_execute_raises_value_error_when_prompt_belongs_to_different_user(
        self, use_case, mock_repository, existing_prompt
    ):
        """Test que verifica que no se puede actualizar prompt de otro usuario."""
        # Arrange
        prompt_id = 1
        user_id = 999  # Usuario diferente
        new_text = "nuevo texto"
        mock_repository.get_by_id.return_value = existing_prompt

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(prompt_id, user_id, new_text)

        assert "no pertenece al usuario" in str(exc_info.value)
        assert str(user_id) in str(exc_info.value)
        mock_repository.get_by_id.assert_called_once_with(prompt_id)
        mock_repository.update.assert_not_called()

    def test_execute_with_long_text(
        self, use_case, mock_repository, existing_prompt
    ):
        """Test que verifica la actualización con texto largo."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "a" * 1000
        updated = SavedPrompt(
            id=1,
            user_id=user_id,
            prompt_text=new_text,
            created_at=existing_prompt.created_at,
        )
        mock_repository.get_by_id.return_value = existing_prompt
        mock_repository.update.return_value = updated

        # Act
        result = use_case.execute(prompt_id, user_id, new_text)

        # Assert
        assert result.prompt_text == new_text
        assert len(result.prompt_text) == 1000

    def test_execute_with_special_characters(
        self, use_case, mock_repository, existing_prompt
    ):
        """Test que verifica la actualización con caracteres especiales."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "texto con áéíóú ñ @#$% 'comillas'"
        updated = SavedPrompt(
            id=1,
            user_id=user_id,
            prompt_text=new_text,
            created_at=existing_prompt.created_at,
        )
        mock_repository.get_by_id.return_value = existing_prompt
        mock_repository.update.return_value = updated

        # Act
        result = use_case.execute(prompt_id, user_id, new_text)

        # Assert
        assert result.prompt_text == new_text

    def test_execute_preserves_other_properties(
        self, use_case, mock_repository, existing_prompt
    ):
        """Test que verifica que se preservan otras propiedades del prompt."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "nuevo texto"
        updated = SavedPrompt(
            id=existing_prompt.id,
            user_id=existing_prompt.user_id,
            prompt_text=new_text,
            created_at=existing_prompt.created_at,
        )
        mock_repository.get_by_id.return_value = existing_prompt
        mock_repository.update.return_value = updated

        # Act
        result = use_case.execute(prompt_id, user_id, new_text)

        # Assert
        assert result.id == existing_prompt.id
        assert result.user_id == existing_prompt.user_id
        assert result.created_at == existing_prompt.created_at

    def test_execute_repository_exception_propagation(
        self, use_case, mock_repository, existing_prompt
    ):
        """Test que verifica que las excepciones del repositorio se propagan."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "nuevo texto"
        mock_repository.get_by_id.return_value = existing_prompt
        mock_repository.update.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(prompt_id, user_id, new_text)

        assert "Database connection failed" in str(exc_info.value)

    def test_execute_calls_repository_methods_in_correct_order(
        self, use_case, mock_repository, existing_prompt, updated_prompt
    ):
        """Test que verifica el orden correcto de las llamadas al repositorio."""
        # Arrange
        prompt_id = 1
        user_id = 617
        new_text = "nuevo texto"
        mock_repository.get_by_id.return_value = existing_prompt
        mock_repository.update.return_value = updated_prompt

        # Act
        use_case.execute(prompt_id, user_id, new_text)

        # Assert
        # Verificar que get_by_id se llama antes que update
        assert mock_repository.get_by_id.call_count == 1
        assert mock_repository.update.call_count == 1
        # get_by_id debe ser la primera llamada
        assert mock_repository.method_calls[0][0] == "get_by_id"
        # update debe ser la segunda llamada
        assert mock_repository.method_calls[1][0] == "update"

    def test_execute_with_different_prompt_ids(
        self, use_case, mock_repository, updated_prompt
    ):
        """Test que verifica la actualización con diferentes IDs de prompt."""
        # Arrange
        prompt_id = 42
        user_id = 617
        new_text = "nuevo texto"
        existing = SavedPrompt(
            id=prompt_id,
            user_id=user_id,
            prompt_text="texto original",
            created_at=datetime.now(),
        )
        mock_repository.get_by_id.return_value = existing
        mock_repository.update.return_value = updated_prompt

        # Act
        use_case.execute(prompt_id, user_id, new_text)

        # Assert
        mock_repository.get_by_id.assert_called_once_with(42)

    def test_execute_with_different_user_ids(
        self, use_case, mock_repository, updated_prompt
    ):
        """Test que verifica la actualización con diferentes IDs de usuario."""
        # Arrange
        prompt_id = 1
        user_id = 999
        new_text = "nuevo texto"
        existing = SavedPrompt(
            id=prompt_id,
            user_id=user_id,
            prompt_text="texto original",
            created_at=datetime.now(),
        )
        mock_repository.get_by_id.return_value = existing
        mock_repository.update.return_value = updated_prompt

        # Act
        result = use_case.execute(prompt_id, user_id, new_text)

        # Assert
        assert result is not None
        mock_repository.get_by_id.assert_called_once_with(prompt_id)

