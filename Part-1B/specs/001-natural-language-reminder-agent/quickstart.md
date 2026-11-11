# Quickstart and Validation

This guide describes how to run and validate the Part-1B reminder CLI after implementation. Application runtime dependencies remain limited to the Python 3.12 standard library.

## Prerequisites

- Python 3.12.
- For live model calls only: a Gemini API key and a model identifier accepted by the Gemini API.
- Development tools: pytest, Ruff, and Bandit.

## Local configuration

From `Part-1B`, copy the placeholder file and edit the local copy:

```powershell
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` and `LLM_MODEL` in `.env`, or set both in the process environment. The process environment takes precedence. `.env` is ignored by the repository; never commit it or print its contents.

## Run a reminder

```powershell
python -m reminder_agent "Remind me to call Sam tomorrow at 9am" --now 2026-11-11T18:00:00
```

Expected behavior: exit 0 and one compact seven-field JSON object on stdout. Relative dates are based on the supplied `--now`, not the computer clock. Invalid arguments produce exit 1 and no JSON; service/network failures produce exit 2 and no JSON.

For a deterministic check without network access, call `core.run(text, now, transport)` with a fake transport that returns a known model response.

## Run the evaluation

The harness invokes `cli.main(argv)` once per case and captures stdout, stderr, and exit code, so it measures the CLI contract rather than bypassing it through `core.run`. Result-producing cases make live model calls; configure credentials first. Empty input makes no model call. Exit code 2 is recorded as `ERROR`, and any `ERROR` makes the overall run `INCONCLUSIVE`. The harness writes `evidence/eval-results.json` with the model name, non-secret settings, per-case results, and overall `PASS`/`FAIL`/`INCONCLUSIVE`. This is committed evidence and must never contain the API key.

```powershell
python .harness/run_eval.py
```

- `PASS`: mean score is at least 0.85, all result-producing cases are schema-valid, the `invalid_input` case meets its CLI outcome contract, and all adversarial and missing-information cases pass fully.
- `FAIL`: at least one evaluation requirement is not met.
- `INCONCLUSIVE`: any case encounters a service failure; those cases are `ERROR`, not `FAIL` or `PASS`.

After each evaluation run, record a human `ACCEPT` or `REJECT` and a short justification in `evidence/harness-log.md`.

## Run tests and quality checks

Tests use fake transports and do not call the network:

```powershell
python -m pytest
ruff check src tests .harness evals
bandit -r src -ll
```

The tests cover result schema and invariants, retry/service-error mapping, CLI exit codes and output streams, `.env` loading without credential disclosure, and evaluation scoring including a simulated service failure. They inject a fake transport through the CLI and never call the network.

## Contract references

- [CLI contract](./contracts/cli.md)
- [Gemini REST contract](./contracts/gemini-rest.md)
- [Reminder result JSON Schema](./contracts/reminder-result.schema.json)
- [Data model](./data-model.md)
