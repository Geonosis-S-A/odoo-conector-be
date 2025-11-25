from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from agent.services.cargar_horas import run_agent_service
from app.shared.security.dependencies import get_current_user
from app.auth.infra.auth_service import JWTPayload
from pydantic import BaseModel
import json
import asyncio

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
    Endpoint para interactuar con el agente de carga de horas con streaming SSE.

    Args:
        request: Petición con el prompt y conversation_id
        current_user: Usuario autenticado (inyectado automáticamente)

    Returns:
        StreamingResponse: Respuesta en streaming SSE (Server-Sent Events)
    """
    # Obtener employee_id del usuario autenticado
    employee_id = current_user["user_id"]

    async def generate_sse():
        """
        Generador asíncrono que envía chunks al cliente en formato SSE.

        SSE es más compatible con proxies/reverse proxies (Railway, nginx, etc.)
        porque el content-type text/event-stream es reconocido como streaming.
        """
        try:
            # Enviar comentario inicial para forzar conexión (algunos proxies lo necesitan)
            yield ": connected\n\n"

            # Usar asyncio.Queue para comunicación entre threads
            loop = asyncio.get_event_loop()
            queue = asyncio.Queue()

            async def producer():
                """Produce chunks desde el generador síncrono en un thread separado."""

                def iterate():
                    for chunk in run_agent_service(
                        request.prompt, request.conversation_id, employee_id
                    ):
                        # Usar call_soon_threadsafe para enviar desde otro thread
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                    loop.call_soon_threadsafe(queue.put_nowait, None)  # Señal de fin

                await asyncio.to_thread(iterate)

            # Iniciar productor en background
            producer_task = asyncio.create_task(producer())

            # Consumir chunks y enviar como SSE
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                # Formato SSE: data: {json}\n\n
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"

            # Esperar a que termine el productor
            await producer_task

            # Enviar evento de finalización
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            # En caso de error, enviar mensaje de error en formato SSE
            error_data = json.dumps(
                {"type": "error", "content": f"❌ Error: {str(e)}"}, ensure_ascii=False
            )
            yield f"data: {error_data}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    # Retornar streaming response con formato SSE
    # text/event-stream es reconocido por proxies como formato de streaming
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "X-Accel-Buffering": "no",  # Desactiva buffering en nginx/Railway
            "Connection": "keep-alive",
        },
    )
