import json
from urllib.error import HTTPError, URLError

import pytest
from reminder_agent.client import (
    GeminiClient,
    ServiceError,
    load_settings,
)

TEST_API_KEY = "unit-test-key-not-a-credential"
MODEL_RESPONSE = {
    "candidates": [
        {"content": {"parts": [{"text": '{"status":"refused"}'}]}}
    ]
}


class FakeResponse:
    def __init__(self, value: object = MODEL_RESPONSE) -> None:
        self.payload = json.dumps(value).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_request_uses_required_headers_payload_and_timeout(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GeminiClient(api_key=TEST_API_KEY, model="test-model")

    client.generate("System instruction", "Reminder text")

    request = captured["request"]
    body = json.loads(request.data)
    assert request.method == "POST"
    assert request.get_header("X-goog-api-key") == TEST_API_KEY
    assert TEST_API_KEY not in request.full_url
    assert captured["timeout"] == 30
    assert body["systemInstruction"]["parts"][0]["text"] == "System instruction"
    assert body["contents"][0]["parts"][0]["text"] == "Reminder text"
    assert body["generationConfig"]["temperature"] == 0.2
    assert body["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.parametrize("status", [429, 503])
def test_retries_only_retryable_http_statuses(monkeypatch, status: int) -> None:
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise HTTPError(request.full_url, status, "temporary", None, None)
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GeminiClient(api_key=TEST_API_KEY, model="test-model")

    client.generate("system", "user")

    assert calls == 3


@pytest.mark.parametrize("status", [429, 503])
def test_exhausted_retryable_http_errors_raise_service_error(
    monkeypatch, status: int
) -> None:
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, status, "temporary", None, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GeminiClient(api_key=TEST_API_KEY, model="test-model")

    with pytest.raises(ServiceError) as error:
        client.generate("system", "user")

    assert calls == 3
    assert TEST_API_KEY not in str(error.value)


@pytest.mark.parametrize(
    "failure",
    [TimeoutError("timeout"), URLError("connection failed")],
)
def test_network_and_timeout_failures_are_not_retried(
    monkeypatch, failure: Exception
) -> None:
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        raise failure

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GeminiClient(api_key=TEST_API_KEY, model="test-model")

    with pytest.raises(ServiceError):
        client.generate("system", "user")

    assert calls == 1


def test_other_http_errors_are_not_retried(monkeypatch) -> None:
    calls = 0

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, 400, "bad request", None, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GeminiClient(api_key=TEST_API_KEY, model="test-model")

    with pytest.raises(HTTPError):
        client.generate("system", "user")

    assert calls == 1


def test_environment_settings_override_dotenv_without_disclosure(
    tmp_path, capsys
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "GEMINI_API_KEY=file-test-key\nLLM_MODEL=file-model\n",
        encoding="utf-8",
    )
    settings = load_settings(
        environment={
            "GEMINI_API_KEY": TEST_API_KEY,
            "LLM_MODEL": "environment-model",
        },
        dotenv_path=dotenv_path,
    )

    assert settings.api_key == TEST_API_KEY
    assert settings.model == "environment-model"
    captured = capsys.readouterr()
    assert TEST_API_KEY not in captured.out
    assert TEST_API_KEY not in captured.err


def test_dotenv_fills_missing_environment_settings(tmp_path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "GEMINI_API_KEY=file-test-key\nLLM_MODEL=file-model\n",
        encoding="utf-8",
    )

    settings = load_settings(environment={}, dotenv_path=dotenv_path)

    assert settings.api_key == "file-test-key"
    assert settings.model == "file-model"
