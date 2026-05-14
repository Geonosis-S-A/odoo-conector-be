"""
Thread IDs del agente: formato u{user_id}_{sufijo} para evitar IDOR en DELETE (VT-13).
"""

from __future__ import annotations

import re

# Sufijo libre (p. ej. UUID); evita ids vacíos o demasiado largos.
_THREAD_RE = re.compile(r"^u(\d+)_(.{1,200})$")


def parse_agent_thread_owner(thread_id: str) -> int | None:
    if not thread_id or not isinstance(thread_id, str):
        return None
    m = _THREAD_RE.match(thread_id.strip())
    if not m:
        return None
    return int(m.group(1))


def thread_owned_by_user(thread_id: str, user_id: int) -> bool:
    owner = parse_agent_thread_owner(thread_id)
    return owner is not None and owner == user_id
