import json
from datetime import datetime

import pytest
from reminder_agent.core import run
from reminder_agent.validation import ValidationError

NOW = datetime.fromisoformat("2026-11-11T09:00:00")
RESULT = {
    "status": "ok",
    "action": "create",
    "title": "Call Sam",
    "remind_at": "2026-11-11T11:00:00",
    "recurrence": "none",
    "clarification_question": None,
    "refusal_reason": None,
}


def test_supplied_now_and_text_are_passed_as_separate_prompt_data() -> None:
    text = "remind me in 2 hours to call Sam"
    received: list[tuple[str, str]] = []

    def transport(system_instruction: str, user_content: str) -> str:
        received.append((system_instruction, user_content))
        return json.dumps(RESULT)

    assert run(text, NOW, transport) == RESULT
    assert len(received) == 1
    system_instruction, user_content = received[0]
    assert "2026-11-11T09:00:00" in system_instruction
    assert text not in system_instruction
    assert user_content == text


def test_core_rejects_invalid_model_result_before_return() -> None:
    invalid_result = {**RESULT, "remind_at": "2026-11-11T09:00:00"}

    with pytest.raises(ValidationError):
        run(
            "remind me in 2 hours to call Sam",
            NOW,
            lambda *_: json.dumps(invalid_result),
        )


def test_core_returns_a_valid_clarification_from_the_model() -> None:
    clarification = {
        "status": "needs_clarification",
        "action": "none",
        "title": None,
        "remind_at": None,
        "recurrence": "none",
        "clarification_question": "What date and time should I use?",
        "refusal_reason": None,
    }

    result = run("remind me to call Sam", NOW, lambda *_: json.dumps(clarification))

    assert result == clarification
