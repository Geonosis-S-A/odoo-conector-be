import redis
from typing import cast

MAX_ATTEMPTS = 10
LOCKOUT_SECONDS = 15 * 60  # 15 minutos
ATTEMPTS_WINDOW_SECONDS = 30 * 60  # Ventana de intentos: 30 minutos


class AccountLockoutService:
    """Rastrea intentos fallidos por cuenta y aplica bloqueo temporal en Redis.

    Claves Redis usadas:
    - auth:attempts:{identifier}  → contador de intentos fallidos (TTL: ATTEMPTS_WINDOW_SECONDS)
    - auth:lockout:{identifier}   → marca de bloqueo activo (TTL: LOCKOUT_SECONDS)
    """

    def __init__(self, redis_client: redis.Redis):  # type: ignore[type-arg]
        self._redis = redis_client

    def _attempts_key(self, identifier: str) -> str:
        return f"auth:attempts:{identifier}"

    def _lockout_key(self, identifier: str) -> str:
        return f"auth:lockout:{identifier}"

    def is_locked(self, identifier: str) -> bool:
        return self._redis.exists(self._lockout_key(identifier)) == 1

    def get_remaining_lockout_seconds(self, identifier: str) -> int:
        ttl = cast(int, self._redis.ttl(self._lockout_key(identifier)))
        return max(ttl, 0)

    def record_failure(self, identifier: str) -> int:
        """Incrementa el contador de fallos. Si alcanza MAX_ATTEMPTS activa el bloqueo.

        Returns:
            Número de intentos fallidos actuales.
        """
        attempts_key = self._attempts_key(identifier)
        count = cast(int, self._redis.incr(attempts_key))
        # Renovar TTL de la ventana en cada intento
        self._redis.expire(attempts_key, ATTEMPTS_WINDOW_SECONDS)

        if count >= MAX_ATTEMPTS:
            lockout_key = self._lockout_key(identifier)
            self._redis.set(lockout_key, "1", ex=LOCKOUT_SECONDS)
            self._redis.delete(attempts_key)

        return count

    def reset(self, identifier: str) -> None:
        """Elimina el contador de intentos tras un acceso exitoso."""
        self._redis.delete(self._attempts_key(identifier))
        self._redis.delete(self._lockout_key(identifier))
