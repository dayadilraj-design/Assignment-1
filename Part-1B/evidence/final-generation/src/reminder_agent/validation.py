import re
from datetime import datetime
from typing import TypeGuard

RESULT_FIELDS = frozenset(
    {
        "status",
        "action",
        "title",
        "remind_at",
        "recurrence",
        "clarification_question",
        "refusal_reason",
    }
)
STATUSES = frozenset({"ok", "needs_clarification", "refused"})
ACTIONS = frozenset({"create", "reschedule", "snooze", "cancel", "none"})
RECURRENCES = frozenset({"none", "daily", "weekly", "monthly"})
DATETIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\Z")
TIMED_ACTIONS = frozenset({"create", "reschedule", "snooze"})
TARGET_ACTIONS = frozenset({"reschedule", "snooze", "cancel"})


class ValidationError(ValueError):
    """Raised when a result violates the reminder contract."""


def _is_string_or_none(value: object) -> TypeGuard[str | None]:
    return value is None or isinstance(value, str)


def parse_local_datetime(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not DATETIME_PATTERN.fullmatch(value):
        raise ValidationError(
            f"{field_name} must use YYYY-MM-DDTHH:MM:SS local format."
        )
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be a real calendar datetime."
        ) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%S") != value:
        raise ValidationError(
            f"{field_name} must use YYYY-MM-DDTHH:MM:SS local format."
        )
    return parsed


def validate_schema(result: object) -> dict[str, object]:
    if not isinstance(result, dict):
        raise ValidationError("Result must be a JSON object.")
    if result.keys() != RESULT_FIELDS:
        raise ValidationError("Result must contain exactly the seven required fields.")
    if not isinstance(result["status"], str) or result["status"] not in STATUSES:
        raise ValidationError("Result status is not allowed.")
    if not isinstance(result["action"], str) or result["action"] not in ACTIONS:
        raise ValidationError("Result action is not allowed.")
    if (
        not isinstance(result["recurrence"], str)
        or result["recurrence"] not in RECURRENCES
    ):
        raise ValidationError("Result recurrence is not allowed.")

    title = result["title"]
    if not _is_string_or_none(title):
        raise ValidationError("Result title must be a string or null.")
    if isinstance(title, str) and not 1 <= len(title) <= 100:
        raise ValidationError("Result title must contain 1 to 100 characters.")

    remind_at = result["remind_at"]
    if remind_at is not None:
        parse_local_datetime(remind_at, field_name="remind_at")
    for field_name in ("clarification_question", "refusal_reason"):
        if not _is_string_or_none(result[field_name]):
            raise ValidationError(f"{field_name} must be a string or null.")
    return result


def validate_result(result: object, now: datetime) -> dict[str, object]:
    if not isinstance(now, datetime) or now.tzinfo is not None:
        raise ValidationError("now must be a naive local datetime.")

    validated = validate_schema(result)
    status = validated["status"]
    action = validated["action"]
    title = validated["title"]
    remind_at = validated["remind_at"]
    question = validated["clarification_question"]
    refusal_reason = validated["refusal_reason"]
    recurrence = validated["recurrence"]

    if status == "ok":
        if action == "none":
            raise ValidationError("An ok result must identify an executable action.")
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("An ok result must include a non-empty target title.")
        if action in TIMED_ACTIONS:
            parsed_remind_at = parse_local_datetime(
                remind_at,
                field_name="remind_at",
            )
            if parsed_remind_at <= now:
                raise ValidationError("remind_at must be strictly later than now.")
        elif action == "cancel" and remind_at is not None:
            raise ValidationError("A cancel result must have a null remind_at.")
        if action in TARGET_ACTIONS and recurrence != "none":
            raise ValidationError(
                "Reschedule, snooze, and cancel recurrence must be none."
            )
        if question is not None or refusal_reason is not None:
            raise ValidationError(
                "An ok result cannot include clarification or refusal text."
            )
        return validated

    if status == "needs_clarification":
        if (
            action != "none"
            or remind_at is not None
            or not isinstance(question, str)
            or not question.strip()
            or not question.endswith("?")
            or refusal_reason is not None
        ):
            raise ValidationError(
                "The needs_clarification result invariants are not met."
            )
        return validated

    if (
        action != "none"
        or title is not None
        or remind_at is not None
        or not isinstance(refusal_reason, str)
        or not refusal_reason.strip()
        or question is not None
    ):
        raise ValidationError("The refused result invariants are not met.")
    return validated
