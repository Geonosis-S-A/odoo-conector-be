import logging
import time
from typing import Any, Callable, List, Optional, Tuple

from app.shared.utils.server_timing import request_started_at

logger = logging.getLogger("step_timer")


class StepTimer:
    """Mide cuánto tarda cada paso de un caso de uso y lo loguea en una línea.

    Sirve para ubicar qué llamadas a Odoo pesan en un request. No altera el
    resultado ni las excepciones de lo que mide.

        timer = StepTimer("timesheet.list")
        rows = timer.call("gateway_all", gateway.all, ...)
        timer.log()

    En el log, ``pre=`` es el tiempo entre que llegó el request y arrancó este
    caso de uso (dependencias, espera del threadpool): si es alto, la demora no
    está en las llamadas a Odoo sino antes de ejecutarlas.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._start = time.perf_counter()
        self._steps: List[Tuple[str, float]] = []
        request_start: Optional[float] = request_started_at.get()
        self._pre_ms: Optional[float] = (
            (self._start - request_start) * 1000 if request_start is not None else None
        )

    def call(self, step: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            self._steps.append((step, (time.perf_counter() - started) * 1000))

    def log(self) -> None:
        total = (time.perf_counter() - self._start) * 1000
        steps = " ".join(f"{step}={ms:.0f}ms" for step, ms in self._steps)
        pre = f" | pre={self._pre_ms:.0f}ms" if self._pre_ms is not None else ""
        logger.info("TIMING %s total=%.0fms | %s%s", self.name, total, steps, pre)
