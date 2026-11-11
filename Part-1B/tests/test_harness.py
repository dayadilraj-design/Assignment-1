import ast
import importlib.util
import json
from pathlib import Path

import pytest
from reminder_agent.client import ServiceError

from reminder_agent import cli

PART_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PART_ROOT / "evals" / "dataset.json"
HARNESS_PATH = PART_ROOT / ".harness" / "run_eval.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("run_eval", HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load evaluation harness from {HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTransport:
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.calls = 0

    def __call__(self, *args: object, **kwargs: object) -> str:
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def result_json(
    *,
    status: str = "ok",
    action: str = "create",
    title: str | None = "Call Sam",
    remind_at: str | None = "2026-11-12T09:00:00",
    clarification_question: str | None = None,
    refusal_reason: str | None = None,
) -> str:
    return json.dumps(
        {
            "status": status,
            "action": action,
            "title": title,
            "remind_at": remind_at,
            "recurrence": "none",
            "clarification_question": clarification_question,
            "refusal_reason": refusal_reason,
        }
    )


def test_harness_invokes_cli_main_once_per_case_and_captures_contract(
    tmp_path, monkeypatch
) -> None:
    harness = load_harness()
    cases = [
        {
            "id": "valid",
            "category": "normal",
            "text": "remind me to call Sam tomorrow at 9am",
            "now": "2026-11-11T09:00:00",
            "expected": {
                "status": "ok",
                "action": "create",
                "remind_at": "2026-11-12T09:00:00",
                "title_keywords": ["Sam"],
            },
        },
        {
            "id": "empty",
            "category": "malformed",
            "text": "",
            "now": "2026-11-11T09:00:00",
            "expected": {
                "outcome": "invalid_input",
                "exit_code": 1,
                "stdout": "",
            },
        },
    ]
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(cases), encoding="utf-8")
    evidence_path = tmp_path / "eval-results.json"
    transports: list[FakeTransport] = []
    invocations: list[list[str]] = []
    secret = "harness-test-key-not-a-credential"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    monkeypatch.setenv("LLM_MODEL", "fake-model")

    def transport_factory(case):
        response = (
            result_json()
            if case["id"] == "valid"
            else result_json(status="needs_clarification", action="none", title=None,
                             remind_at=None,
                             clarification_question="What time should I use?")
        )
        transport = FakeTransport(response)
        transports.append(transport)
        return transport

    def recording_cli_main(argv, transport=None):
        invocations.append(list(argv))
        return cli.main(argv, transport=transport)

    report = harness.run_evaluation(
        dataset_path,
        cli_main=recording_cli_main,
        transport_factory=transport_factory,
        evidence_path=evidence_path,
        model_name="fake-model",
        settings={"temperature": 0.2},
    )

    assert len(invocations) == len(cases)
    assert invocations[0][0] == cases[0]["text"]
    assert invocations[1][0] == ""
    assert [transport.calls for transport in transports] == [1, 0]
    assert report["cases"][0]["exit_code"] == 0
    assert report["cases"][0]["stdout"].endswith("\n")
    assert report["cases"][1]["exit_code"] == 1
    assert report["cases"][1]["stdout"] == ""
    assert report["cases"][1]["status"] == "PASS"
    serialized_evidence = evidence_path.read_text(encoding="utf-8")
    assert secret not in serialized_evidence
    assert "fake-model" in serialized_evidence


def test_harness_does_not_call_core_run_directly() -> None:
    source = HARNESS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node.func
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    ]

    assert any(
        isinstance(function, ast.Attribute)
        and function.attr == "main"
        and isinstance(function.value, ast.Name)
        and function.value.id == "cli"
        for function in calls
    )
    assert not any(
        isinstance(function, ast.Attribute)
        and function.attr == "run"
        and isinstance(function.value, ast.Attribute)
        and function.value.attr == "core"
        for function in calls
    )
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.endswith(".core")
        for node in ast.walk(tree)
    )


def test_scoring_weights_and_pass_gate() -> None:
    harness = load_harness()

    assert harness.weighted_score(1.0, 0.5, 0.0) == pytest.approx(0.5)
    assert harness.overall_status(
        mean_score=0.85,
        case_results=[{"status": "PASS"}],
    ) == "PASS"
    assert harness.overall_status(
        mean_score=0.849,
        case_results=[{"status": "PASS"}],
    ) == "FAIL"


def test_service_failure_is_error_and_makes_run_inconclusive(
    tmp_path,
) -> None:
    harness = load_harness()
    case = {
        "id": "service-failure",
        "category": "normal",
        "text": "remind me tomorrow at 9am to call Sam",
        "now": "2026-11-11T09:00:00",
        "expected": {
            "status": "ok",
            "action": "create",
            "remind_at": "2026-11-12T09:00:00",
            "title_keywords": ["Sam"],
        },
    }
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps([case]), encoding="utf-8")
    transport = FakeTransport(ServiceError("service unavailable"))

    report = harness.run_evaluation(
        dataset_path,
        cli_main=cli.main,
        transport_factory=lambda _: transport,
        evidence_path=tmp_path / "eval-results.json",
        model_name="fake-model",
        settings={"temperature": 0.2},
    )

    assert transport.calls == 1
    assert report["cases"][0]["status"] == "ERROR"
    assert report["overall"] == "INCONCLUSIVE"
    assert harness.overall_status(
        mean_score=1.0,
        case_results=[{"status": "ERROR"}],
    ) == "INCONCLUSIVE"


def test_dataset_has_required_shape_categories_and_fixed_evaluation_rules() -> None:
    harness = load_harness()
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    categories = {}

    assert len(cases) >= 18
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert {"id", "category", "text", "now", "expected"} <= case.keys()
        categories[case["category"]] = categories.get(case["category"], 0) + 1
        assert isinstance(case["text"], str)
        assert isinstance(case["now"], str)

    assert categories["normal"] >= 6
    assert categories["boundary"] >= 3
    assert categories["ambiguous"] >= 3
    assert categories["missing_information"] >= 2
    assert categories["malformed"] >= 2
    assert categories["adversarial"] >= 2
    assert any(
        case["text"] == ""
        and case["expected"].get("outcome") == "invalid_input"
        for case in cases
    )
    assert harness.SCORE_WEIGHTS == {
        "schema": 0.3,
        "invariants": 0.4,
        "semantic": 0.3,
    }
    assert harness.PASS_THRESHOLD == 0.85
