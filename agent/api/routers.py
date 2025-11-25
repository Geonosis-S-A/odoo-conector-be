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

    # Crear generador para streaming con SSE (Server-Sent Events)
    async def generate():
        """Generador asíncrono que envía chunks al cliente en formato SSE."""
        try:
            # Enviar comentario inicial para establecer la conexión SSE inmediatamente
            # Esto es crítico para Railway y otros proxies que buferizan
            yield ": SSE connection established\n\n"

            # Enviar evento de inicio
            yield f"data: {json.dumps({'type': 'start', 'content': ''}, ensure_ascii=False)}\n\n"

            for chunk in run_agent_service(
                request.prompt, request.conversation_id, employee_id
            ):
                # Enviar cada chunk en formato SSE
                # Formato: "data: {json}\n\n"
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            # En caso de error, enviar mensaje de error en formato SSE
            error_chunk = {"type": "error", "content": f"❌ Error: {str(e)}"}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

        finally:
            # Siempre enviar señal de finalización
            done_chunk = {"type": "done"}
            yield f"data: {json.dumps(done_chunk, ensure_ascii=False)}\n\n"

    # Retornar streaming response con formato SSE
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",  # SSE es mejor reconocido por proxies
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",  # Para nginx
            "Connection": "keep-alive",
            "Content-Encoding": "none",  # Evitar compresión que causa buffering
        },
    )
