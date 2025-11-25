from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from agent.services.cargar_horas import run_agent_service
from app.shared.security.dependencies import get_current_user
from app.auth.infra.auth_service import JWTPayload
from pydantic import BaseModel
import json

router = APIRouter(prefix="/agent", tags=["agent"])


class CargarHorasAgentRequest(BaseModel):
    """Schema para la petición de carga de horas del agente."""

    prompt: str
    conversation_id: str


@router.post("/cargar-horas-agent")
async def cargar_horas_agent(
    request: CargarHorasAgentRequest,
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Endpoint para interactuar con el agente de carga de horas con streaming.

    Args:
        request: Petición con el prompt y conversation_id
        current_user: Usuario autenticado (inyectado automáticamente)

    Returns:
        StreamingResponse: Respuesta en streaming con chunks de texto
    """
    # Obtener employee_id del usuario autenticado
    employee_id = current_user["user_id"]

    # Crear generador para streaming con JSON
    async def generate():
        """Generador asíncrono que envía chunks al cliente en formato JSON."""
        try:
            # Enviar un chunk inicial vacío inmediatamente para activar el streaming
            # Esto fuerza a los proxies a comenzar a transmitir
            yield (
                json.dumps({"type": "start", "content": ""}, ensure_ascii=False) + "\n"
            )

            for chunk in run_agent_service(
                request.prompt, request.conversation_id, employee_id
            ):
                # Enviar cada chunk como JSON completo
                yield json.dumps(chunk, ensure_ascii=False) + "\n"
        except Exception as e:
            # En caso de error, enviar mensaje de error como JSON
            error_chunk = {"type": "error", "content": f"❌ Error: {str(e)}"}
            yield json.dumps(error_chunk, ensure_ascii=False) + "\n"
            # Enviar señal de finalización
            done_chunk = {"type": "done"}
            yield json.dumps(done_chunk, ensure_ascii=False) + "\n"

    # Retornar streaming response con JSON y headers adicionales
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",  # Newline Delimited JSON
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Encoding": "none",  # Previene compresión que puede causar buffering
            "X-Accel-Buffering": "no",  # Deshabilita buffering en nginx
            "X-Content-Type-Options": "nosniff",  # Previene que el navegador bufferice
        },
    )
