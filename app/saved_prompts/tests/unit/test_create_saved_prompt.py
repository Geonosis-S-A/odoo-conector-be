import pytest
from unittest.mock import Mock
from datetime import datetime

from app.saved_prompts.application.use_cases.create_saved_prompt import (
    CreateSavedPromptUseCase,
)
from app.saved_prompts.domain.models import SavedPrompt
from app.saved_prompts.domain.repositories import SavedPromptRepository


class TestCreateSavedPromptUseCase:
    @pytest.fixture
    def mock_repository(self):
        """Fixture que proporciona un repositorio mockeado."""
        return Mock(spec=SavedPromptRepository)

    @pytest.fixture
    def use_case(self, mock_repository):
        """Fixture que proporciona el caso de uso con el repositorio mockeado."""
        return CreateSavedPromptUseCase(mock_repository)

    @pytest.fixture
    def sample_saved_prompt(self):
        """Fixture que proporciona un SavedPrompt de prueba."""
        return SavedPrompt(
            id=1,
            user_id=617,
            prompt_text="cargame 8 horas en SX1 para hoy",
            created_at=datetime(2024, 11, 25, 10, 30, 0),
        )

    def test_execute_creates_saved_prompt_successfully(
        self, use_case, mock_repository, sample_saved_prompt
    ):
        """Test que verifica la creación exitosa de un prompt guardado."""
        # Arrange
        user_id = 617
        prompt_text = "cargame 8 horas en SX1 para hoy"
        mock_repository.create.return_value = sample_saved_prompt

        # Act
        result = use_case.execute(user_id, prompt_text)

        # Assert
        assert result == sample_saved_prompt
        mock_repository.create.assert_called_once()
        created_prompt = mock_repository.create.call_args[0][0]
        assert created_prompt.user_id == user_id
        assert created_prompt.prompt_text == prompt_text
        assert created_prompt.id is None  # No tiene ID antes de guardarse

    def test_execute_trims_whitespace_from_prompt_text(
        self, use_case, mock_repository, sample_saved_prompt
    ):
        """Test que verifica que se eliminan espacios en blanco del prompt."""
        # Arrange
        user_id = 617
        prompt_text = "  cargame 8 horas en SX1 para hoy  "  # Con espacios
        mock_repository.create.return_value = sample_saved_prompt

        # Act
        result = use_case.execute(user_id, prompt_text)

        # Assert
        mock_repository.create.assert_called_once()
        created_prompt = mock_repository.create.call_args[0][0]
        assert created_prompt.prompt_text == prompt_text.strip()
        assert not created_prompt.prompt_text.startswith(" ")
        assert not created_prompt.prompt_text.endswith(" ")

    def test_execute_raises_value_error_for_empty_prompt_text(self, use_case):
        """Test que verifica que no se pueden crear prompts vacíos."""
        # Arrange
        user_id = 617
        prompt_text = ""  # Texto vacío

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(user_id, prompt_text)

        assert "El texto del prompt no puede estar vacío" in str(exc_info.value)

    def test_execute_raises_value_error_for_whitespace_only_prompt_text(self, use_case):
        """Test que verifica que no se pueden crear prompts con solo espacios."""
        # Arrange
        user_id = 617
        prompt_text = "   "  # Solo espacios en blanco

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(user_id, prompt_text)

        assert "El texto del prompt no puede estar vacío" in str(exc_info.value)

    def test_execute_with_different_user_ids(self, use_case, mock_repository):
        """Test que verifica la creación para diferentes user_ids."""
        # Arrange
        user_id = 999
        prompt_text = "cargar 4 horas en proyecto ABC"
        created_prompt = SavedPrompt(
            id=5,
            user_id=user_id,
            prompt_text=prompt_text,
            created_at=datetime.now(),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        result = use_case.execute(user_id, prompt_text)

        # Assert
        assert result.user_id == user_id
        mock_repository.create.assert_called_once()

    def test_execute_with_long_prompt_text(self, use_case, mock_repository):
        """Test que verifica la creación con texto largo."""
        # Arrange
        user_id = 617
        prompt_text = "a" * 1000  # Texto muy largo
        created_prompt = SavedPrompt(
            id=1,
            user_id=user_id,
            prompt_text=prompt_text,
            created_at=datetime.now(),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        result = use_case.execute(user_id, prompt_text)

        # Assert
        assert result is not None
        assert len(result.prompt_text) == 1000
        assert result.prompt_text == prompt_text
        mock_repository.create.assert_called_once()

    def test_execute_with_special_characters_in_prompt(self, use_case, mock_repository):
        """Test que verifica la creación con caracteres especiales."""
        # Arrange
        user_id = 617
        prompt_text = "cargame 8hs en proyecto 'SX-1' con descripción: áéíóú ñ @#$%"
        created_prompt = SavedPrompt(
            id=1,
            user_id=user_id,
            prompt_text=prompt_text,
            created_at=datetime.now(),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        result = use_case.execute(user_id, prompt_text)

        # Assert
        assert result.prompt_text == prompt_text
        mock_repository.create.assert_called_once()

    def test_execute_repository_exception_propagation(self, use_case, mock_repository):
        """Test que verifica que las excepciones del repositorio se propagan."""
        # Arrange
        user_id = 617
        prompt_text = "test prompt"
        mock_repository.create.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(user_id, prompt_text)

        assert "Database connection failed" in str(exc_info.value)
        mock_repository.create.assert_called_once()

    def test_execute_creates_saved_prompt_with_multiline_text(
        self, use_case, mock_repository
    ):
        """Test que verifica la creación con texto multilínea."""
        # Arrange
        user_id = 617
        prompt_text = """cargame 8 horas en SX1
        con descripción de desarrollo
        para toda la semana"""
        created_prompt = SavedPrompt(
            id=1,
            user_id=user_id,
            prompt_text=prompt_text.strip(),
            created_at=datetime.now(),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        result = use_case.execute(user_id, prompt_text)

        # Assert
        assert result is not None
        mock_repository.create.assert_called_once()

    def test_execute_returns_prompt_with_id_from_repository(
        self, use_case, mock_repository
    ):
        """Test que verifica que el prompt retornado incluye ID del repositorio."""
        # Arrange
        user_id = 617
        prompt_text = "test prompt"
        created_prompt = SavedPrompt(
            id=123,  # ID asignado por la base de datos
            user_id=user_id,
            prompt_text=prompt_text,
            created_at=datetime.now(),
        )
        mock_repository.create.return_value = created_prompt

        # Act
        result = use_case.execute(user_id, prompt_text)

        # Assert
        assert result.id is not None
        assert result.id == 123
        assert result.user_id == user_id
        assert result.prompt_text == prompt_text
