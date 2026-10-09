import logging
import time
from typing import Any, Callable, List, Tuple

logger = logging.getLogger("step_timer")


class StepTimer:
    """Mide cuánto tarda cada paso de un caso de uso y lo loguea en una línea.

    Sirve para ubicar qué llamadas a Odoo pesan en un request. No altera el
    resultado ni las excepciones de lo que mide.

        timer = StepTimer("timesheet.list")
        rows = timer.call("gateway_all", gateway.all, ...)
        timer.log()
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._start = time.perf_counter()
        self._steps: List[Tuple[str, float]] = []

    def call(self, step: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            self._steps.append((step, (time.perf_counter() - started) * 1000))

    def log(self) -> None:
        total = (time.perf_counter() - self._start) * 1000
        steps = " ".join(f"{step}={ms:.0f}ms" for step, ms in self._steps)
        logger.info("TIMING %s total=%.0fms | %s", self.name, total, steps)
