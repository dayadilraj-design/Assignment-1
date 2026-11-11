import json
from datetime import datetime

import pytest

from reminder_agent import cli
from reminder_agent.client import ServiceError

NOW = "2026-11-11T09:00:00"

RESULTS = [
    {
        "status": "ok",
        "action": "create",
        "title": "Call Sam",
        "remind_at": "2026-11-12T09:00:00",
        "recurrence": "none",
        "clarification_question": None,
        "refusal_reason": None,
    },
    {
        "status": "needs_clarification",
        "action": "none",
        "title": None,
        "remind_at": None,
        "recurrence": "none",
        "clarification_question": "When should I remind you?",
        "refusal_reason": None,
    },
    {
        "status": "refused",
        "action": "none",
        "title": None,
        "remind_at": None,
        "recurrence": "none",
        "clarification_question": None,
        "refusal_reason": "I can only help with reminders.",
    },
]


class FakeTransport:
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.calls = 0

    def __call__(self, *args: object, **kwargs: object) -> str:
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.mark.parametrize("result", RESULTS, ids=lambda item: item["status"])
def test_result_statuses_emit_one_compact_json_object(
    result: dict[str, object], capsys
) -> None:
    transport = FakeTransport(json.dumps(result))

    exit_code = cli.main(
        ["remind me to call Sam tomorrow at 9am", "--now", NOW],
        transport=transport,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == json.dumps(result, separators=(",", ":")) + "\n"
    assert captured.err == ""
    assert transport.calls == 1


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_or_whitespace_text_is_rejected_before_transport(
    text: str, capsys
) -> None:
    transport = FakeTransport(json.dumps(RESULTS[0]))

    exit_code = cli.main([text, "--now", NOW], transport=transport)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.strip()
    assert transport.calls == 0


@pytest.mark.parametrize(
    "now",
    ["invalid", "2026-11-11T09:00:00+05:30", "2026-02-30T09:00:00"],
)
def test_invalid_now_is_rejected_before_transport(now: str, capsys) -> None:
    transport = FakeTransport(json.dumps(RESULTS[0]))

    exit_code = cli.main(["remind me to call Sam", "--now", now], transport=transport)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.strip()
    assert transport.calls == 0


def test_invalid_model_json_is_an_application_error(capsys) -> None:
    transport = FakeTransport("not-json")

    exit_code = cli.main(
        ["remind me to call Sam tomorrow at 9am", "--now", NOW],
        transport=transport,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.strip()


def test_service_error_uses_exit_two_without_result_or_secret(
    capsys,
) -> None:
    secret = "unit-test-key-not-a-credential"
    transport = FakeTransport(ServiceError(f"failed request using {secret}"))

    exit_code = cli.main(
        ["remind me to call Sam tomorrow at 9am", "--now", NOW],
        transport=transport,
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.strip()
    assert secret not in captured.out
    assert secret not in captured.err


def test_cli_rejects_offset_aware_datetime_even_if_parseable(capsys) -> None:
    transport = FakeTransport(json.dumps(RESULTS[0]))
    parsed = datetime.fromisoformat("2026-11-11T09:00:00+05:30")
    assert parsed.utcoffset() is not None

    exit_code = cli.main(
        ["remind me to call Sam", "--now", parsed.isoformat()],
        transport=transport,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err.strip()
    assert transport.calls == 0
