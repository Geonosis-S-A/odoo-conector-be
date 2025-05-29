import pytest
import asyncio
import logging
import json
from unittest.mock import patch, MagicMock
from fastapi import Request, FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.main import generic_exception_handler


class TestGenericExceptionHandler:
    """Tests para el handler de excepciones genérico."""

    def test_generic_exception_handler_returns_500(self):
        """Verifica que el handler retorne status code 500."""
        # Arrange
        request = MagicMock(spec=Request)
        exception = Exception("Test exception")

        # Act
        with patch("app.main.logger") as mock_logger:
            response = asyncio.run(generic_exception_handler(request, exception))

        # Assert
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    def test_generic_exception_handler_returns_correct_message(self):
        """Verifica que el handler retorne el mensaje correcto."""
        # Arrange
        request = MagicMock(spec=Request)
        exception = Exception("Test exception")

        # Act
        with patch("app.main.logger") as mock_logger:
            response = asyncio.run(generic_exception_handler(request, exception))

        # Assert
        # Verificar el contenido usando el diccionario content que se pasó al JSONResponse
        expected_content = {"detail": "Ocurrió un error inesperado. Intenta más tarde."}
        assert json.loads(response.body) == expected_content

    @patch("app.main.logger")
    def test_generic_exception_handler_logs_error(self, mock_logger):
        """Verifica que el handler loguee el error correctamente."""
        # Arrange
        request = MagicMock(spec=Request)
        exception = Exception("Test exception")

        # Act
        asyncio.run(generic_exception_handler(request, exception))

        # Assert
        mock_logger.error.assert_called_once_with(
            f"Error inesperado: {exception}", exc_info=True
        )

    def test_different_exception_types_handled_correctly(self):
        """Verifica que diferentes tipos de excepciones se manejen igual."""
        test_exceptions = [
            ValueError("Value error test"),
            RuntimeError("Runtime error test"),
            KeyError("Key error test"),
            AttributeError("Attribute error test"),
        ]

        request = MagicMock(spec=Request)
        expected_content = {"detail": "Ocurrió un error inesperado. Intenta más tarde."}

        for exception in test_exceptions:
            with patch("app.main.logger"):
                response = asyncio.run(generic_exception_handler(request, exception))

            # Todas las excepciones deben retornar el mismo resultado
            assert response.status_code == 500
            assert json.loads(response.body) == expected_content

    @patch("app.main.logger")
    def test_handler_preserves_original_exception_info(self, mock_logger):
        """Verifica que el handler preserve la información completa de la excepción original."""
        # Arrange
        request = MagicMock(spec=Request)
        original_message = "This is a test exception with specific details"
        exception = ValueError(original_message)

        # Act
        asyncio.run(generic_exception_handler(request, exception))

        # Assert
        mock_logger.error.assert_called_once()
        logged_message = mock_logger.error.call_args[0][0]
        assert original_message in str(logged_message)
        assert mock_logger.error.call_args[1]["exc_info"] is True

    @patch("app.main.logger")
    def test_handler_with_empty_exception_message(self, mock_logger):
        """Verifica que el handler maneje excepciones sin mensaje."""
        # Arrange
        request = MagicMock(spec=Request)
        exception = Exception()  # Excepción sin mensaje

        # Act
        response = asyncio.run(generic_exception_handler(request, exception))

        # Assert
        assert response.status_code == 500
        expected_content = {"detail": "Ocurrió un error inesperado. Intenta más tarde."}
        assert json.loads(response.body) == expected_content
        mock_logger.error.assert_called_once_with(
            f"Error inesperado: {exception}", exc_info=True
        )

    @patch("app.main.logger")
    def test_handler_response_structure(self, mock_logger):
        """Verifica que la estructura de respuesta sea correcta."""
        # Arrange
        request = MagicMock(spec=Request)
        exception = Exception("Test exception")

        # Act
        response = asyncio.run(generic_exception_handler(request, exception))

        # Assert
        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body)

        # Verificar que tiene la clave 'detail'
        assert "detail" in response_data
        assert isinstance(response_data["detail"], str)
        assert (
            response_data["detail"] == "Ocurrió un error inesperado. Intenta más tarde."
        )

        # Verificar que no tiene información sensible de la excepción
        assert "Test exception" not in response_data["detail"]

    @patch("app.main.logger")
    def test_handler_content_type_is_json(self, mock_logger):
        """Verifica que el content-type de la respuesta sea JSON."""
        # Arrange
        request = MagicMock(spec=Request)
        exception = Exception("Test exception")

        # Act
        response = asyncio.run(generic_exception_handler(request, exception))

        # Assert
        assert response.media_type == "application/json"
