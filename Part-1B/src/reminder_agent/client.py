import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

API_KEY_ENV = "GEMINI_API_KEY"
MODEL_ENV = "LLM_MODEL"
TEMPERATURE = 0.2
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
RETRYABLE_STATUSES = frozenset({429, 503})
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
_ORIGINAL_URLOPEN = urllib.request.urlopen


class ServiceError(RuntimeError):
    """Raised when the model service cannot be reached successfully."""


class ConfigurationError(ValueError):
    """Raised when required model configuration is unavailable."""


class GeminiResponseError(ValueError):
    """Raised when Gemini returns an unusable response envelope."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str


def _read_dotenv(path: Path) -> dict[str, str]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise ConfigurationError("Unable to read local model configuration.") from exc

    values: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        name, separator, value = stripped.partition("=")
        if not separator or name.strip() not in {API_KEY_ENV, MODEL_ENV}:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name.strip()] = value
    return values


def load_settings(
    environment: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> Settings:
    process_environment = os.environ if environment is None else environment
    names = (API_KEY_ENV, MODEL_ENV)
    values = {
        name: process_environment.get(name, "").strip()
        for name in names
    }

    if any(not values[name] for name in names):
        config_path = Path.cwd() / ".env" if dotenv_path is None else dotenv_path
        file_values = _read_dotenv(config_path)
        for name in names:
            if not values[name]:
                values[name] = file_values.get(name, "").strip()

    missing = [name for name in names if not values[name]]
    if missing:
        raise ConfigurationError(
            "Missing required model configuration: " + ", ".join(missing) + "."
        )
    return Settings(api_key=values[API_KEY_ENV], model=values[MODEL_ENV])


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: int = TIMEOUT_SECONDS,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ConfigurationError("GEMINI_API_KEY must not be empty.")
        if not model or not model.strip():
            raise ConfigurationError("LLM_MODEL must not be empty.")
        if timeout != TIMEOUT_SECONDS or max_attempts != MAX_ATTEMPTS:
            raise ValueError("Gemini request timeout and attempt limits are fixed.")
        self._api_key = api_key
        self.model = model
        self.timeout = TIMEOUT_SECONDS
        self.max_attempts = MAX_ATTEMPTS

    def generate(self, system_instruction: str, user_content: str) -> str:
        model_path = urllib.parse.quote(self.model, safe="-_.")
        endpoint = f"{GEMINI_API_ROOT}/{model_path}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {
                "temperature": TEMPERATURE,
                "responseMimeType": "application/json",
            },
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self._api_key,
            },
        )
        if urllib.parse.urlsplit(request.full_url).scheme != "https":
            raise ValueError("Gemini requests must use HTTPS.")
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler())
        response_data: bytes | None = None
        for attempt in range(self.max_attempts):
            try:
                # Preserve compatibility with tests replacing urlopen with a fake.
                patched_urlopen = getattr(urllib.request, "urlopen")
                if patched_urlopen is not _ORIGINAL_URLOPEN:
                    response_context = patched_urlopen(request, timeout=self.timeout)
                else:
                    response_context = opener.open(request, timeout=self.timeout)
                with response_context as response:
                    response_data = response.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code not in RETRYABLE_STATUSES:
                    raise
                if attempt + 1 == self.max_attempts:
                    raise ServiceError(
                        "Gemini service returned a retryable error after all attempts."
                    ) from exc
            except (TimeoutError, urllib.error.URLError, OSError) as exc:
                raise ServiceError("Gemini service request failed.") from exc

        if response_data is None:
            raise ServiceError("Gemini service request failed.")
        return self._extract_candidate_text(response_data)

    @staticmethod
    def _extract_candidate_text(response_data: bytes) -> str:
        try:
            envelope = json.loads(response_data.decode("utf-8"))
            candidates = envelope["candidates"]
            parts = candidates[0]["content"]["parts"]
            text = "".join(part["text"] for part in parts if "text" in part)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise GeminiResponseError("Gemini returned an unusable response.") from exc
        if not text.strip():
            raise GeminiResponseError("Gemini returned an empty response.")
        return text


def default_transport(system_instruction: str, user_content: str) -> str:
    settings = load_settings()
    client = GeminiClient(settings.api_key, settings.model)
    return client.generate(system_instruction, user_content)
