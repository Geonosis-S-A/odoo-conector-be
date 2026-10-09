import asyncio
import logging

from app.shared.utils.server_timing import inflight_requests, threadpool_usage

logger = logging.getLogger("loop_lag")


async def monitor_event_loop_lag(interval: float = 0.25, threshold: float = 0.5) -> None:
    """Avisa cuando el event loop tarda en volver a ejecutarse.

    Pide dormir ``interval`` s y mide cuánto tardó de más. Un atraso alto indica
    que algo ejecutó código bloqueante en el loop (por ejemplo, un endpoint
    ``async def`` que llama a Odoo de forma síncrona) y que mientras tanto no se
    atendió ningún otro request.
    """
    loop = asyncio.get_running_loop()
    while True:
        started = loop.time()
        await asyncio.sleep(interval)
        lag = loop.time() - started - interval
        if lag >= threshold:
            logger.info(
                "EVENT LOOP LAG %.0fms inflight=%d threadpool=%s",
                lag * 1000,
                inflight_requests(),
                threadpool_usage(),
            )
