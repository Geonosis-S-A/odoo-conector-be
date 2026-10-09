import logging
import time
from contextvars import ContextVar
from typing import Optional

logger = logging.getLogger("server_timing")

# Desde cuándo (perf_counter) está en curso el request actual. Lo fija el
# middleware y los endpoints sync lo heredan en el threadpool: permite saber
# cuánto pasó desde que llegó el request hasta que arrancó el caso de uso.
request_started_at: ContextVar[Optional[float]] = ContextVar(
    "request_started_at", default=None
)

# Un request que tarda más que esto se loguea (método, ruta y query, sin headers).
SLOW_REQUEST_MS = 1000


class ServerTimingMiddleware:
    """Agrega ``Server-Timing: app;dur=<ms>`` a cada respuesta HTTP.

    Mide desde que la app recibe el request hasta que arranca la respuesta
    (dependencias, endpoint y espera del threadpool). En las DevTools del
    navegador aparece en Network > Timing (o en los Response Headers) y sirve
    para separar lo que tarda el servidor de lo que se pierde en la red o en el
    navegador: ``Waiting for server response`` menos este valor.

    Los requests más lentos que ``SLOW_REQUEST_MS`` se loguean, para compararlos
    con el tiempo del caso de uso (líneas ``TIMING``).

    Es ASGI puro (no ``BaseHTTPMiddleware``) para no sumar costo por request y
    para que el contexto llegue a los endpoints.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        token = request_started_at.set(started)
        status_code = 0

        async def send_with_timing(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                elapsed_ms = (time.perf_counter() - started) * 1000
                headers = list(message.get("headers", []))
                headers.append((b"server-timing", f"app;dur={elapsed_ms:.0f}".encode()))
                message["headers"] = headers
                if elapsed_ms >= SLOW_REQUEST_MS:
                    query = scope.get("query_string", b"").decode("latin-1")
                    logger.info(
                        "SLOW REQUEST %s %s%s status=%s app=%.0fms",
                        scope.get("method", "-"),
                        scope.get("path", "-"),
                        f"?{query}" if query else "",
                        status_code,
                        elapsed_ms,
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_with_timing)
        finally:
            request_started_at.reset(token)
