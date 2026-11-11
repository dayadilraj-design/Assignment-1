import json
import os
import tempfile
from pathlib import Path
from typing import Any

from todo.models import Task, TodoError, ValidationError


class StorageError(TodoError):
    """Raised when task data cannot be read, validated, or written."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def load_tasks(path: Path) -> tuple[list[Task], int]:
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], 1
    except (OSError, UnicodeError) as exc:
        raise StorageError(f"could not read task data file '{path}': {exc}") from exc

    try:
        document = json.loads(
            contents,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise StorageError(f"invalid task data file '{path}': {exc}") from exc

    if type(document) is not dict or set(document) != {"version", "next_id", "tasks"}:
        raise StorageError("task data must contain exactly version, next_id, and tasks")
    if type(document["version"]) is not int or document["version"] != 1:
        raise StorageError("unsupported task data version")

    next_id = document["next_id"]
    if type(next_id) is not int or next_id <= 0:
        raise StorageError("next_id must be a positive integer")

    stored_tasks = document["tasks"]
    if not isinstance(stored_tasks, list):
        raise StorageError("tasks must be a list")

    tasks: list[Task] = []
    identifiers: set[int] = set()
    try:
        for stored_task in stored_tasks:
            task = Task.from_dict(stored_task)
            if task.id in identifiers:
                raise StorageError(f"duplicate task ID: {task.id}")
            identifiers.add(task.id)
            tasks.append(task)
    except ValidationError as exc:
        raise StorageError(f"invalid task in data file '{path}': {exc}") from exc

    if identifiers and next_id <= max(identifiers):
        raise StorageError("next_id must be greater than every task ID")
    return tasks, next_id


def save_tasks(path: Path, tasks: list[Task], next_id: int) -> None:
    if type(next_id) is not int or next_id <= 0:
        raise StorageError("next_id must be a positive integer")
    if tasks and next_id <= max(task.id for task in tasks):
        raise StorageError("next_id must be greater than every task ID")

    document = {
        "version": 1,
        "next_id": next_id,
        "tasks": [task.to_dict() for task in tasks],
    }
    serialized = json.dumps(document, separators=(",", ":")) + "\n"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as exc:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                raise StorageError(
                    f"could not clean up temporary task data file: {cleanup_error}"
                ) from cleanup_error
        raise StorageError(f"could not write task data file '{path}': {exc}") from exc
