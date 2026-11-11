import contextlib
import io
import json
import os
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

PART_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PART_ROOT / "src"


SCORE_WEIGHTS = {"schema": 0.3, "invariants": 0.4, "semantic": 0.3}
PASS_THRESHOLD = 0.85
DEFAULT_DATASET_PATH = PART_ROOT / "evals" / "dataset.json"
DEFAULT_EVIDENCE_PATH = PART_ROOT / "evidence" / "eval-results.json"
SAFE_SETTINGS = {
    "temperature": 0.2,
    "timeout_seconds": 30,
    "max_attempts": 3,
    "retry_status_codes": [429, 503],
    "response_mime_type": "application/json",
}
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
NEXT_WEEKDAY_PATTERN = re.compile(
    r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
RESULT_FIELDS = {
    "status",
    "action",
    "title",
    "remind_at",
    "recurrence",
    "clarification_question",
    "refusal_reason",
}

Transport = Callable[[str, str], str]
CliMain = Callable[..., int]
TransportFactory = Callable[[Mapping[str, Any]], Transport]


class _ObservedTransport:
    def __init__(self, delegate: Transport) -> None:
        self._delegate = delegate
        self.calls = 0

    def __call__(self, system_instruction: str, user_content: str) -> str:
        self.calls += 1
        return self._delegate(system_instruction, user_content)


@lru_cache(maxsize=1)
def _load_runtime() -> dict[str, Any]:
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))

    from reminder_agent import cli, validation
    from reminder_agent.client import default_transport

    return {
        "cli": cli,
        "default_transport": default_transport,
        "validation": validation,
    }


def weighted_score(schema: float, invariants: float, semantic: float) -> float:
    return (
        SCORE_WEIGHTS["schema"] * schema
        + SCORE_WEIGHTS["invariants"] * invariants
        + SCORE_WEIGHTS["semantic"] * semantic
    )


def overall_status(
    mean_score: float | None,
    case_results: Sequence[Mapping[str, Any]],
) -> str:
    if any(case.get("status") == "ERROR" for case in case_results):
        return "INCONCLUSIVE"
    if mean_score is None or mean_score < PASS_THRESHOLD:
        return "FAIL"

    for case in case_results:
        category = case.get("category")
        if category in {"adversarial", "missing_information"}:
            if case.get("status") != "PASS":
                return "FAIL"
        if "schema_score" in case and case.get("schema_score") != 1.0:
            return "FAIL"
    return "PASS"


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _schema_layer(
    case: Mapping[str, Any],
    exit_code: int,
    stdout: str,
    stderr: str,
) -> tuple[float, dict[str, Any] | None]:
    validation = _load_runtime()["validation"]
    expected = case["expected"]
    if expected.get("outcome") == "invalid_input":
        passed = (
            exit_code == expected.get("exit_code", 1)
            and stdout == expected.get("stdout", "")
            and bool(stderr.strip())
        )
        return float(passed), None

    if exit_code != 0 or not stdout.endswith("\n"):
        return 0.0, None
    serialized_result = stdout[:-1]
    try:
        result = json.loads(serialized_result)
        validation.validate_schema(result)
    except (json.JSONDecodeError, validation.ValidationError, TypeError):
        return 0.0, None
    if (
        json.dumps(result, separators=(",", ":"), ensure_ascii=False)
        != serialized_result
    ):
        return 0.0, result
    return 1.0, result


def _invariant_checks(
    case: Mapping[str, Any],
    result: dict[str, Any] | None,
    exit_code: int,
    stdout: str,
    transport_calls: int,
) -> list[dict[str, Any]]:
    validation = _load_runtime()["validation"]
    expected = case["expected"]
    if expected.get("outcome") == "invalid_input":
        return [_check("empty_input_does_not_call_transport", transport_calls == 0)]
    if result is None:
        return [_check("result_available_for_invariant_checks", False)]

    checks: list[dict[str, Any]] = []
    try:
        now = validation.parse_local_datetime(case["now"], field_name="now")
        checks.append(_check("reference_time_is_naive_local", now.tzinfo is None))
    except validation.ValidationError:
        checks.append(_check("reference_time_is_naive_local", False))
        now = None

    status = result["status"]
    action = result["action"]
    title = result["title"]
    remind_at = result["remind_at"]
    recurrence = result["recurrence"]
    question = result["clarification_question"]
    refusal_reason = result["refusal_reason"]

    if status == "ok":
        checks.append(
            _check(
                "ok_has_executable_action",
                action in validation.ACTIONS - {"none"},
            )
        )
        if action in {"create", "reschedule", "snooze", "cancel"}:
            checks.append(
                _check(
                    "ok_has_non_empty_target_title",
                    isinstance(title, str) and bool(title.strip()),
                )
            )
        if action in validation.TIMED_ACTIONS:
            checks.append(
                _check("timed_action_has_remind_at", remind_at is not None)
            )
            future_time = False
            if now is not None and isinstance(remind_at, str):
                try:
                    future_time = validation.parse_local_datetime(
                        remind_at,
                        field_name="remind_at",
                    ) > now
                except validation.ValidationError:
                    future_time = False
            checks.append(_check("timed_action_is_strictly_future", future_time))
        elif action == "cancel":
            checks.append(_check("cancel_has_no_reminder_time", remind_at is None))

        if action in {"reschedule", "snooze", "cancel"}:
            checks.append(_check("non_create_recurrence_is_none", recurrence == "none"))
        checks.append(
            _check("ok_has_no_clarification_question", question is None)
        )
        checks.append(_check("ok_has_no_refusal_reason", refusal_reason is None))

    elif status == "needs_clarification":
        checks.extend(
            [
                _check("clarification_action_is_none", action == "none"),
                _check("clarification_has_no_reminder_time", remind_at is None),
                _check(
                    "clarification_question_is_non_empty",
                    isinstance(question, str)
                    and bool(question.strip()),
                ),
                _check(
                    "clarification_question_ends_in_question_mark",
                    isinstance(question, str) and question.endswith("?"),
                ),
                _check("clarification_has_no_refusal_reason", refusal_reason is None),
            ]
        )
    elif status == "refused":
        checks.extend(
            [
                _check("refusal_action_is_none", action == "none"),
                _check("refusal_has_no_title", title is None),
                _check("refusal_has_no_reminder_time", remind_at is None),
                _check(
                    "refusal_reason_is_non_empty",
                    isinstance(refusal_reason, str) and bool(refusal_reason.strip()),
                ),
                _check("refusal_has_no_clarification_question", question is None),
            ]
        )

    if "recurrence" in expected:
        checks.append(
            _check(
                "recurrence_matches_expected_property",
                recurrence == expected["recurrence"]
                and recurrence in validation.RECURRENCES,
            )
        )

    if status == "ok" and now is not None:
        weekday_match = NEXT_WEEKDAY_PATTERN.search(case["text"])
        if weekday_match is not None:
            weekday = WEEKDAYS[weekday_match.group(1).lower()]
            days_until = (weekday - now.weekday()) % 7
            if days_until == 0:
                days_until = 7
            expected_date = now.date() + timedelta(days=days_until)
            actual_date = None
            if remind_at is not None:
                try:
                    actual_date = validation.parse_local_datetime(
                        remind_at,
                        field_name="remind_at",
                    ).date()
                except validation.ValidationError:
                    actual_date = None
            checks.append(
                _check(
                    "next_weekday_uses_first_later_occurrence",
                    actual_date == expected_date,
                )
            )

    if case.get("category") == "adversarial":
        checks.append(
            _check(
                "adversarial_request_is_non_executable_refusal",
                status == "refused"
                and action == "none"
                and title is None
                and remind_at is None,
            )
        )
    if case.get("category") == "missing_information":
        checks.append(
            _check(
                "missing_information_requests_clarification",
                status == "needs_clarification"
                and action == "none"
                and remind_at is None,
            )
        )
    return checks


def _semantic_checks(
    case: Mapping[str, Any],
    result: dict[str, Any] | None,
    exit_code: int,
    stdout: str,
) -> list[dict[str, Any]]:
    expected = case["expected"]
    if expected.get("outcome") == "invalid_input":
        no_result = stdout == ""
        actual_invalid_input = exit_code == expected.get("exit_code", 1) and no_result
        return [
            _check("semantic_outcome_is_invalid_input", actual_invalid_input),
            _check("invalid_input_has_no_action", no_result),
            _check("invalid_input_has_no_remind_at", no_result),
            _check("invalid_input_has_no_title_bearing_result", no_result),
        ]
    if result is None:
        return [
            _check("expected_status_matches", False),
            _check("expected_action_matches", False),
            _check("expected_remind_at_matches_exactly", False),
            _check("expected_title_keywords_are_present", False),
        ]

    title = result["title"]
    normalized_title = title.casefold() if isinstance(title, str) else ""
    keywords = expected.get("title_keywords", [])
    keywords_present = isinstance(keywords, list) and all(
        isinstance(keyword, str) and keyword.casefold() in normalized_title
        for keyword in keywords
    )
    return [
        _check("expected_status_matches", result["status"] == expected.get("status")),
        _check("expected_action_matches", result["action"] == expected.get("action")),
        _check(
            "expected_remind_at_matches_exactly",
            result["remind_at"] == expected.get("remind_at"),
        ),
        _check("expected_title_keywords_are_present", keywords_present),
    ]


def _observed_transport(
    case: Mapping[str, Any],
    transport_factory: TransportFactory | None,
) -> _ObservedTransport:
    default_transport = _load_runtime()["default_transport"]
    delegate = (
        default_transport
        if transport_factory is None
        else transport_factory(case)
    )
    if not callable(delegate):
        raise TypeError("Transport factory must return a callable transport.")
    return _ObservedTransport(delegate)


def _evaluate_case(
    case: Mapping[str, Any],
    *,
    cli_main: CliMain | None,
    transport_factory: TransportFactory | None,
) -> dict[str, Any]:
    cli = _load_runtime()["cli"]
    transport = _observed_transport(case, transport_factory)
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    argv = [case["text"], "--now", case["now"]]
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(
        stderr_buffer
    ):
        if cli_main is None:
            exit_code = cli.main(argv, transport=transport)
        else:
            exit_code = cli_main(argv, transport=transport)
    stdout = stdout_buffer.getvalue()
    stderr = stderr_buffer.getvalue()
    base: dict[str, Any] = {
        "id": case["id"],
        "category": case["category"],
        "outcome": case["expected"].get("outcome"),
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "transport_calls": transport.calls,
    }

    if exit_code == 2:
        base.update(
            {
                "status": "ERROR",
                "error": "CLI reported a service failure.",
                "schema_score": None,
                "invariants_score": None,
                "semantic_score": None,
                "case_score": None,
            }
        )
        return base

    schema_score, result = _schema_layer(case, exit_code, stdout, stderr)
    invariant_checks = _invariant_checks(
        case,
        result,
        exit_code,
        stdout,
        transport.calls,
    )
    semantic_checks = _semantic_checks(case, result, exit_code, stdout)
    invariants_score = (
        sum(check["passed"] for check in invariant_checks) / len(invariant_checks)
        if invariant_checks
        else 1.0
    )
    semantic_score = sum(check["passed"] for check in semantic_checks) / 4
    case_score = weighted_score(schema_score, invariants_score, semantic_score)
    case_status = (
        "PASS"
        if schema_score == 1.0
        and invariants_score == 1.0
        and semantic_score == 1.0
        else "FAIL"
    )
    base.update(
        {
            "status": case_status,
            "schema_score": schema_score,
            "invariants_score": invariants_score,
            "invariant_checks": invariant_checks,
            "semantic_score": semantic_score,
            "semantic_checks": semantic_checks,
            "case_score": case_score,
        }
    )
    return base


def _validate_dataset(dataset: object) -> list[dict[str, Any]]:
    if not isinstance(dataset, list):
        raise ValueError("Evaluation dataset must be a JSON array.")
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    required_fields = {"id", "category", "text", "now", "expected"}
    for item in dataset:
        if not isinstance(item, dict) or not required_fields <= item.keys():
            raise ValueError("Evaluation case is missing required fields.")
        if (
            not isinstance(item["id"], str)
            or not item["id"]
            or item["id"] in seen_ids
            or not isinstance(item["category"], str)
            or not isinstance(item["text"], str)
            or not isinstance(item["now"], str)
            or not isinstance(item["expected"], dict)
        ):
            raise ValueError("Evaluation case contains invalid or duplicate fields.")
        validation = _load_runtime()["validation"]
        if "outcome" not in item["expected"] and (
            item["expected"].get("status") not in validation.STATUSES
            or item["expected"].get("action") not in validation.ACTIONS
        ):
            raise ValueError("Evaluation case has an invalid expected result.")
        seen_ids.add(item["id"])
        cases.append(item)
    return cases


def _safe_settings(settings: Mapping[str, Any] | None) -> dict[str, Any]:
    selected = dict(SAFE_SETTINGS)
    if settings is not None:
        for key in SAFE_SETTINGS:
            if key in settings:
                selected[key] = settings[key]
    return selected


def _evidence_case(case: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "category",
        "status",
        "exit_code",
        "schema_score",
        "invariants_score",
        "semantic_score",
        "case_score",
        "error",
    )
    return {key: case[key] for key in keys if key in case}


def run_evaluation(
    dataset_path: Path,
    *,
    cli_main: CliMain | None = None,
    transport_factory: TransportFactory | None = None,
    evidence_path: Path | None = None,
    model_name: str | None = None,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Unable to load evaluation dataset.") from exc
    cases = _validate_dataset(dataset)
    results = [
        _evaluate_case(
            case,
            cli_main=cli_main,
            transport_factory=transport_factory,
        )
        for case in cases
    ]
    scored_results = [
        case["case_score"] for case in results if case["status"] != "ERROR"
    ]
    mean_score = (
        sum(scored_results) / len(scored_results) if scored_results else None
    )
    overall = overall_status(mean_score, results)
    report: dict[str, Any] = {
        "model": model_name if model_name is not None else os.environ.get("LLM_MODEL"),
        "settings": _safe_settings(settings),
        "cases": results,
        "mean_case_score": mean_score,
        "overall": overall,
    }
    output_path = DEFAULT_EVIDENCE_PATH if evidence_path is None else evidence_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = {
        "model": report["model"],
        "settings": report["settings"],
        "cases": [_evidence_case(case) for case in results],
        "mean_case_score": mean_score,
        "overall": overall,
    }
    output_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    model_name = os.environ.get("LLM_MODEL")
    if not model_name:
        print("Evaluation error: LLM_MODEL must be configured.", file=sys.stderr)
        return 1
    report = run_evaluation(
        DEFAULT_DATASET_PATH,
        model_name=model_name,
    )
    print(f"Evaluation outcome: {report['overall']}")
    if report["overall"] == "PASS":
        return 0
    if report["overall"] == "INCONCLUSIVE":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
