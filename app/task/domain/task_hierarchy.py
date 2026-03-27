"""Utilidades para armar el nombre completo de una tarea (jerarquía en Odoo)."""

from __future__ import annotations

from typing import Dict, List

from app.task.domain.gateway import TaskGateway
from app.task.domain.models import TaskWithParentInfo


def collect_tasks_info_with_ancestors(
    task_gateway: TaskGateway, task_ids: List[int]
) -> Dict[int, TaskWithParentInfo]:
    """Obtiene TaskWithParentInfo para cada id y para todos los ancestros necesarios."""
    if not task_ids:
        return {}

    tasks_info: Dict[int, TaskWithParentInfo] = {}
    pending = list({task_id for task_id in task_ids if task_id})

    for _ in range(25):
        if not pending:
            break
        batch = task_gateway.get_tasks_info_with_parents(pending)
        tasks_info.update(batch)
        next_pending: List[int] = []
        for info in batch.values():
            if info.parent_id and info.parent_id not in tasks_info:
                next_pending.append(info.parent_id)
        pending = list({pid for pid in next_pending if pid})

    return tasks_info


def full_task_display_name(
    task_id: int, tasks_info: Dict[int, TaskWithParentInfo]
) -> str:
    """Cadena padre → … → hoja, igual que en el listado aplanado del frontend."""
    chain: List[str] = []
    current_id: int | None = task_id
    seen: set[int] = set()

    while current_id is not None and current_id not in seen:
        seen.add(current_id)
        info = tasks_info.get(current_id)
        if info is None:
            break
        chain.append(info.name)
        current_id = info.parent_id

    chain.reverse()
    return " → ".join(chain) if chain else ""
