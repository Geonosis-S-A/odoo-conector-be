from unittest.mock import Mock

from app.task.domain.models import TaskWithParentInfo
from app.task.domain.task_hierarchy import (
    collect_tasks_info_with_ancestors,
    full_task_display_name,
)


def test_full_task_display_name_single_level():
    tasks = {
        10: TaskWithParentInfo(
            id=10, name="Hoja", project_id=1, project_name="P",
            parent_id=None, parent_name=None,
        )
    }
    assert full_task_display_name(10, tasks) == "Hoja"


def test_full_task_display_name_three_levels():
    tasks = {
        1: TaskWithParentInfo(
            id=1, name="Raíz", project_id=1, project_name="P",
            parent_id=None, parent_name=None,
        ),
        2: TaskWithParentInfo(
            id=2, name="Media", project_id=1, project_name="P",
            parent_id=1, parent_name="Raíz",
        ),
        3: TaskWithParentInfo(
            id=3, name="Hoja", project_id=1, project_name="P",
            parent_id=2, parent_name="Media",
        ),
    }
    assert full_task_display_name(3, tasks) == "Raíz → Media → Hoja"


def test_collect_tasks_info_with_ancestors_fetches_parents():
    gateway = Mock()
    leaf = TaskWithParentInfo(
        id=3, name="Hoja", project_id=1, project_name="P",
        parent_id=2, parent_name="Media",
    )
    mid = TaskWithParentInfo(
        id=2, name="Media", project_id=1, project_name="P",
        parent_id=1, parent_name="Raíz",
    )
    root = TaskWithParentInfo(
        id=1, name="Raíz", project_id=1, project_name="P",
        parent_id=None, parent_name=None,
    )

    def side_effect(ids):
        return {i: {3: leaf, 2: mid, 1: root}[i] for i in ids if i in {1, 2, 3}}

    gateway.get_tasks_info_with_parents.side_effect = side_effect

    result = collect_tasks_info_with_ancestors(gateway, [3])
    assert full_task_display_name(3, result) == "Raíz → Media → Hoja"
    assert gateway.get_tasks_info_with_parents.call_count >= 1
