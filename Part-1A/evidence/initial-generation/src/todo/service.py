from collections.abc import Sequence
from pathlib import Path

from todo.models import PRIORITIES, STATUSES, Task, TodoError, ValidationError
from todo.storage import load_tasks, save_tasks


class TaskNotFoundError(TodoError):
    """Raised when a requested task ID is not present."""


class IllegalTransitionError(TodoError):
    """Raised when a recognized status transition is not allowed."""


_PRIORITY_ORDER = {priority: index for index, priority in enumerate(reversed(PRIORITIES))}
_ALLOWED_TRANSITIONS = {
    ("todo", "doing"),
    ("doing", "done"),
    ("doing", "todo"),
}


def add_task(
    path: Path,
    title: str,
    priority: str = "medium",
    tags: Sequence[str] | None = None,
) -> Task:
    tasks, next_id = load_tasks(path)
    task = Task(
        id=next_id,
        title=title,
        priority=priority,
        tags=tuple(tags) if tags is not None else (),
        status="todo",
    )
    tasks.append(task)
    save_tasks(path, tasks, next_id + 1)
    return task


def list_tasks(path: Path, tag: str | None = None) -> list[Task]:
    if tag is not None and (not isinstance(tag, str) or not tag):
        raise ValidationError("tag filter must not be empty")

    tasks, _ = load_tasks(path)
    if tag is not None:
        tasks = [task for task in tasks if tag in task.tags]
    return sorted(tasks, key=lambda task: (_PRIORITY_ORDER[task.priority], task.id))


def edit_task(
    path: Path,
    task_id: int,
    *,
    title: str | None = None,
    priority: str | None = None,
    tags: Sequence[str] | None = None,
    clear_tags: bool = False,
) -> Task:
    if title is None and priority is None and tags is None and not clear_tags:
        raise ValidationError("edit requires at least one edit option")
    if tags is not None and clear_tags:
        raise ValidationError("--tag and --clear-tags cannot be used together")

    tasks, next_id = load_tasks(path)
    for index, existing in enumerate(tasks):
        if existing.id != task_id:
            continue
        updated = Task(
            id=existing.id,
            title=title if title is not None else existing.title,
            priority=priority if priority is not None else existing.priority,
            tags=(
                ()
                if clear_tags
                else tuple(tags)
                if tags is not None
                else existing.tags
            ),
            status=existing.status,
        )
        tasks[index] = updated
        save_tasks(path, tasks, next_id)
        return updated
    raise TaskNotFoundError(f"task not found: {task_id}")


def set_status(path: Path, task_id: int, status: str) -> Task:
    if status not in STATUSES:
        raise ValidationError(f"invalid status: {status}")

    tasks, next_id = load_tasks(path)
    for index, existing in enumerate(tasks):
        if existing.id != task_id:
            continue
        if (existing.status, status) not in _ALLOWED_TRANSITIONS:
            raise IllegalTransitionError(
                f"illegal transition from '{existing.status}' to '{status}'"
            )
        updated = Task(
            id=existing.id,
            title=existing.title,
            priority=existing.priority,
            tags=existing.tags,
            status=status,
        )
        tasks[index] = updated
        save_tasks(path, tasks, next_id)
        return updated
    raise TaskNotFoundError(f"task not found: {task_id}")


def delete_task(path: Path, task_id: int) -> int:
    tasks, next_id = load_tasks(path)
    for index, task in enumerate(tasks):
        if task.id == task_id:
            del tasks[index]
            save_tasks(path, tasks, next_id)
            return task_id
    raise TaskNotFoundError(f"task not found: {task_id}")
