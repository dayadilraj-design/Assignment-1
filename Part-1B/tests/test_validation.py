from copy import deepcopy
from datetime import datetime

import pytest
from reminder_agent.validation import ValidationError, validate_result

NOW = datetime.fromisoformat("2026-11-11T09:00:00")


def create_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "ok",
        "action": "create",
        "title": "Call Sam",
        "remind_at": "2026-11-12T09:00:00",
        "recurrence": "none",
        "clarification_question": None,
        "refusal_reason": None,
    }
    result.update(overrides)
    return result


def test_accepts_valid_create_result() -> None:
    validate_result(create_result(), NOW)


@pytest.mark.parametrize(
    "change",
    [
        {"missing": "title"},
        {"extra": "unexpected"},
    ],
)
def test_rejects_missing_or_extra_fields(change: dict[str, str]) -> None:
    result = create_result()
    if "missing" in change:
        del result[change["missing"]]
    else:
        result[change["extra"]] = "value"

    with pytest.raises(ValidationError):
        validate_result(result, NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "pending"),
        ("action", "delete"),
        ("recurrence", "yearly"),
    ],
)
def test_rejects_disallowed_enum_values(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        validate_result(create_result(**{field: value}), NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", None),
        ("action", None),
        ("title", 42),
        ("remind_at", 42),
        ("recurrence", None),
        ("clarification_question", 42),
        ("refusal_reason", []),
    ],
)
def test_rejects_fields_with_invalid_types(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        validate_result(create_result(**{field: value}), NOW)


@pytest.mark.parametrize("title", ["", "x" * 101, 42])
def test_rejects_invalid_title(title: object) -> None:
    with pytest.raises(ValidationError):
        validate_result(create_result(title=title), NOW)


def test_accepts_title_at_maximum_length() -> None:
    validate_result(create_result(title="x" * 100), NOW)


@pytest.mark.parametrize("recurrence", ["none", "daily", "weekly", "monthly"])
def test_accepts_allowed_recurrence_values(recurrence: str) -> None:
    validate_result(create_result(recurrence=recurrence), NOW)


@pytest.mark.parametrize(
    "remind_at",
    ["2026-11-12T09:00", "2026-02-30T09:00:00", "2026-11-12T09:00:00Z"],
)
def test_rejects_malformed_or_impossible_remind_at(remind_at: str) -> None:
    with pytest.raises(ValidationError):
        validate_result(create_result(remind_at=remind_at), NOW)


@pytest.mark.parametrize("action", ["create", "reschedule", "snooze"])
@pytest.mark.parametrize("remind_at", ["2026-11-11T09:00:00", "2026-11-11T08:59:59"])
def test_timed_ok_actions_require_strictly_future_time(
    action: str, remind_at: str
) -> None:
    with pytest.raises(ValidationError):
        validate_result(create_result(action=action, remind_at=remind_at), NOW)


def test_ok_result_requires_an_executable_action_and_null_reasons() -> None:
    with pytest.raises(ValidationError):
        validate_result(create_result(action="none"), NOW)

    with pytest.raises(ValidationError):
        validate_result(
            create_result(clarification_question="What time?"),
            NOW,
        )

    with pytest.raises(ValidationError):
        validate_result(create_result(refusal_reason="I cannot help."), NOW)


@pytest.mark.parametrize("action", ["reschedule", "snooze", "cancel"])
def test_non_create_actions_require_target_title_and_no_recurrence(
    action: str,
) -> None:
    remind_at = None if action == "cancel" else "2026-11-12T09:00:00"
    base = create_result(
        action=action,
        remind_at=remind_at,
        recurrence="none",
    )
    validate_result(base, NOW)

    with pytest.raises(ValidationError):
        validate_result({**base, "title": ""}, NOW)

    with pytest.raises(ValidationError):
        validate_result({**base, "recurrence": "daily"}, NOW)


def test_cancel_requires_null_remind_at() -> None:
    with pytest.raises(ValidationError):
        validate_result(create_result(action="cancel"), NOW)


def test_needs_clarification_invariants() -> None:
    result = create_result(
        status="needs_clarification",
        action="none",
        title=None,
        remind_at=None,
        clarification_question="When should I remind you?",
    )
    validate_result(result, NOW)

    invalid_results = [
        {**result, "action": "create"},
        {**result, "remind_at": "2026-11-12T09:00:00"},
        {**result, "clarification_question": ""},
        {**result, "clarification_question": "When? "},
        {**result, "refusal_reason": "not allowed"},
    ]
    for invalid in invalid_results:
        with pytest.raises(ValidationError):
            validate_result(invalid, NOW)


def test_refused_invariants() -> None:
    result = create_result(
        status="refused",
        action="none",
        title=None,
        remind_at=None,
        refusal_reason="I can only help with reminders.",
    )
    validate_result(result, NOW)

    invalid_results = [
        {**result, "action": "create"},
        {**result, "title": "Call Sam"},
        {**result, "remind_at": "2026-11-12T09:00:00"},
        {**result, "refusal_reason": ""},
        {**result, "clarification_question": "Can I help with a reminder?"},
    ]
    for invalid in invalid_results:
        with pytest.raises(ValidationError):
            validate_result(invalid, NOW)


def test_result_is_not_mutated_during_validation() -> None:
    result = create_result()
    original = deepcopy(result)

    validate_result(result, NOW)

    assert result == original
