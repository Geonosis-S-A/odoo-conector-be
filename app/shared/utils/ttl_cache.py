import copy
import threading
import time
from typing import Any, Dict, Hashable, Tuple


class TtlCache:
    """Caché en memoria del proceso, con vencimiento por entrada.

    Thread-safe (los endpoints sync corren en un threadpool). ``ttl_seconds <= 0``
    la deshabilita: ``get`` siempre falla y ``set`` no guarda nada.

    Los valores se copian al guardar y al leer, para que quien los reciba no
    pueda modificar lo que otros requests van a leer.
    """

    def __init__(self, ttl_seconds: float, max_size: int = 5000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._data: Dict[Hashable, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.ttl_seconds > 0

    def get(self, key: Hashable) -> Tuple[bool, Any]:
        """Devuelve ``(hit, valor)``. Distingue un valor guardado de un miss."""
        if not self.enabled:
            return False, None
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False, None
            expires_at, value = entry
            if expires_at <= time.monotonic():
                del self._data[key]
                return False, None
        return True, copy.deepcopy(value)

    def set(self, key: Hashable, value: Any) -> None:
        if not self.enabled:
            return
        stored = copy.deepcopy(value)
        with self._lock:
            if len(self._data) >= self.max_size:
                self._evict()
            self._data[key] = (time.monotonic() + self.ttl_seconds, stored)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def _evict(self) -> None:
        """Con el lock tomado: quita lo vencido y, si no alcanza, lo más viejo."""
        now = time.monotonic()
        for key in [k for k, (exp, _) in self._data.items() if exp <= now]:
            del self._data[key]
        if len(self._data) >= self.max_size:
            oldest = min(self._data, key=lambda k: self._data[k][0])
            del self._data[oldest]
