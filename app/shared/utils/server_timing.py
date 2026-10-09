import time


class ServerTimingMiddleware:
    """Agrega ``Server-Timing: app;dur=<ms>`` a cada respuesta HTTP.

    Mide desde que la app recibe el request hasta que arranca la respuesta
    (dependencias, endpoint y espera del threadpool). En las DevTools del
    navegador aparece en Network > Timing (o en los Response Headers) y sirve
    para separar lo que tarda el servidor de lo que se pierde en la red o en el
    navegador: ``Waiting for server response`` menos este valor.

    Es ASGI puro (no ``BaseHTTPMiddleware``) para no sumar costo por request.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()

        async def send_with_timing(message) -> None:
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - started) * 1000
                headers = list(message.get("headers", []))
                headers.append((b"server-timing", f"app;dur={elapsed_ms:.0f}".encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_timing)
