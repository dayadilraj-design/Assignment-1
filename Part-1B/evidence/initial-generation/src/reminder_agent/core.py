import json
from collections.abc import Callable
from datetime import datetime

from .client import default_transport
from .prompt import build_prompt
from .validation import ValidationError, validate_result

Transport = Callable[[str, str], str]


def run(
    text: str,
    now: datetime,
    transport: Transport | None = None,
) -> dict[str, object]:
    if not text.strip():
        raise ValueError("Reminder text must not be empty.")
    if now.tzinfo is not None:
        raise ValueError("now must be a naive local datetime.")

    system_instruction, user_content = build_prompt(text, now)
    active_transport = transport if transport is not None else default_transport
    response_text = active_transport(system_instruction, user_content)
    try:
        model_result = json.loads(response_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValidationError("The model response is not valid JSON.") from exc
    return validate_result(model_result, now)
