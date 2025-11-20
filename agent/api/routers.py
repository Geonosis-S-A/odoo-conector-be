from fastapi import APIRouter, Depends, Body
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
    current_user: JWTPayload = Depends(get_current_user)
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
        import json
        
        try:
            for chunk in run_agent_service(request.prompt, request.conversation_id, employee_id):
                # Verificar el tipo de chunk
                if chunk['type'] == 'event':
                    # Enviar evento especial (ej: timesheet_created)
                    # Formato SSE: event: <nombre>\ndata: <datos>\n\n
                    event_name = chunk.get('event', 'message')
                    event_data = json.dumps(chunk.get('content', {}))
                    yield f"event: {event_name}\ndata: {event_data}\n\n"
                else:
                    # Enviar texto normal
                    # Formato: data: <contenido>\n\n
                    yield f"data: {chunk['content']}\n\n"
        except Exception as e:
            # En caso de error, enviar mensaje de error como evento SSE
            error_msg = json.dumps(f"❌ Error: {str(e)}")
            yield f"data: {error_msg}\n\n"
            yield "data: [DONE]\n\n"
    
    # Retornar streaming response con SSE
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Deshabilita buffering en nginx
        }
    )
