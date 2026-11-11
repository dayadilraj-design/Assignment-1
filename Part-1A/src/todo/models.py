from dataclasses import dataclass
from typing import Any

PRIORITIES = ("low", "medium", "high")
STATUSES = ("todo", "doing", "done")
TASK_FIELDS = ("id", "title", "priority", "tags", "status")


class TodoError(Exception):
    """Base class for expected CLI errors."""


class ValidationError(TodoError):
    """Raised when a task value is invalid."""


def _normalize_tags(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValidationError("tags must be a list of strings")

    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValidationError("tags must contain only strings")
        tag = value.strip()
        if not tag:
            raise ValidationError("tags must not be empty")
        if tag in seen:
            raise ValidationError(f"duplicate tag: {tag}")
        seen.add(tag)
        tags.append(tag)
    return tuple(tags)


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    priority: str
    tags: tuple[str, ...]
    status: str

    def __post_init__(self) -> None:
        if type(self.id) is not int or self.id <= 0:
            raise ValidationError("task ID must be a positive integer")
        if not isinstance(self.title, str):
            raise ValidationError("title must be a string")
        title = self.title.strip()
        if not title:
            raise ValidationError("title must not be empty")
        if self.priority not in PRIORITIES:
            raise ValidationError("priority must be low, medium, or high")
        if self.status not in STATUSES:
            raise ValidationError("status must be todo, doing, or done")

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "tags", _normalize_tags(self.tags))

    @classmethod
    def from_dict(cls, data: Any) -> "Task":
        if type(data) is not dict or set(data) != set(TASK_FIELDS):
            raise ValidationError("task must contain exactly the required fields")
        if type(data["id"]) is not int:
            raise ValidationError("task ID must be a positive integer")
        if not isinstance(data["tags"], list):
            raise ValidationError("tags must be a list of strings")
        return cls(
            id=data["id"],
            title=data["title"],
            priority=data["priority"],
            tags=tuple(data["tags"]),
            status=data["status"],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "tags": list(self.tags),
            "status": self.status,
        }
