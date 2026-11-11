# Implementation Plan: Natural-Language Reminder Agent

**Branch**: `001-natural-language-reminder-agent` | **Date**: 2026-11-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-natural-language-reminder-agent/spec.md`

## Summary

Build a stateless Python 3.12 command-line agent that sends one untrusted reminder request and an explicit naive local reference datetime to Gemini, validates the returned seven-field result locally, and emits one compact JSON object only for valid result-producing requests. Keep the production runtime standard-library-only; isolate the HTTPS client behind an injectable transport so tests can run without network access. The evaluation harness will invoke every dataset case through `cli.main(argv)`, capture stdout, stderr, and exit code, score schema/CLI contract, applicable invariants, and semantic expectations, and distinguish service errors from failed evaluations.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library at runtime (`urllib`, `json`, `datetime`, `argparse`, `pathlib`); `pytest`, `ruff`, and `bandit` are development tools only.

**Storage**: No application database or persistent reminder storage. Evaluation input is a checked-in JSON dataset; evaluation results are committed evidence at `evidence/eval-results.json`.

**Testing**: `pytest` with injected fake transports; targeted validator, client retry/error, CLI, environment-loading, and harness tests. The harness tests exercise `cli.main(argv)` with captured stdout/stderr and a fake transport, including invalid input and service failures.

**Target Platform**: Cross-platform Python 3.12 command-line environments with HTTPS access for live model calls.

**Project Type**: Single Python CLI project.

**Performance Goals**: One model request per valid reminder case, with a 30-second timeout per attempt and no more than three total attempts for HTTP 429/503. No additional throughput target is specified.

**Constraints**: Standard-library-only application runtime; Gemini REST over HTTPS; API key only from the environment or ignored `.env`; model from `LLM_MODEL`; fixed temperature 0.2; local naive `--now`; exact seven-field validated result; no JSON on invalid input, application error, or service failure; evaluation threshold fixed at 0.85.

**Scale/Scope**: One request per process invocation, no reminder persistence, at least 18 evaluation cases, and exactly one CLI invocation per case per harness run. Result-producing cases make one model request, subject to the specified HTTP 429/503 retry policy; invalid input makes no model call.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-design gate

- **Standard-library runtime**: PASS. The application uses Python 3.12 standard-library modules only; pytest, Ruff, and Bandit are development tools, not runtime dependencies.
- **Stable validated contract**: PASS. The shared JSON Schema describes the exact result shape, and the local validator enforces cross-field invariants before output.
- **Safe clarification and refusal**: PASS. The system instruction treats request text as untrusted data; missing information yields clarification, and unsafe or unrelated requests yield non-executable refusal.
- **Credential and service boundaries**: PASS. Use `x-goog-api-key`, environment-over-`.env` precedence, the existing git-ignored `.env`, fixed temperature/timeout/retry rules, and distinct application/service errors. Never log, emit, or commit the API key; committed evaluation evidence contains only the model name, non-secret settings, per-case results, and overall outcome.
- **Simplicity and safe implementation**: PASS. Use a single package, one injectable transport boundary, no persistence, and no dynamic execution or unsafe serialization.
- **Quality and evaluation workflow**: PASS. Preserve the 0.85 threshold, one CLI-driven harness, the 18-case category minimums, all three evaluation layers, service `ERROR`/overall `INCONCLUSIVE`, committed evaluation evidence, the human acceptance log, and the two-repair-attempt limit.
- **Empty-input evaluation compatibility**: RESOLVED. The accepted clarification distinguishes the result JSON Schema from a separate no-JSON CLI outcome contract for the `invalid_input` case. That case must exit 1, emit no stdout JSON, provide a safe stderr diagnostic, and make no model call; it is still run through the three evaluation layers and weighted scoring.

**Gate result**: PASS. No constitution violations or unresolved design blockers remain.

### Post-design gate

- The selected module boundaries preserve the standard-library runtime and injectable network boundary.
- The result schema is locally authoritative; Gemini structured output is only a generation aid.
- CLI output and the evaluation evidence omit credentials. The model name appears only where required as evaluation metadata and is not included in CLI output.
- Tests and evaluation support deterministic offline execution through fake transports.

**Post-design gate result**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-natural-language-reminder-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── cli.md
    ├── gemini-rest.md
    └── reminder-result.schema.json
```

### Source Code (repository root: `Part-1B/`)

```text
src/
└── reminder_agent/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── client.py
    ├── core.py
    ├── prompt.py
    └── validation.py

tests/
├── test_cli.py
├── test_client.py
├── test_core.py
├── test_harness.py
└── test_validation.py

.harness/
└── run_eval.py

evals/
└── dataset.json

evidence/
├── eval-results.json       # committed evaluation evidence; never includes the API key
└── harness-log.md          # human ACCEPT/REJECT record

.env.example
../README.md                # Git-root README; document both parts and Part-1B run commands
```

**Structure Decision**: Use the single-project CLI layout under `Part-1B/`. `cli.py` owns argument parsing, input checks, exit codes, and stdout/stderr. `core.py` coordinates prompt construction, the injected transport, JSON decoding, and validation. `client.py` owns configuration and Gemini HTTPS. `prompt.py` contains model instructions and time-of-day defaults. `validation.py` is the authoritative local result validator. The harness invokes `cli.main(argv)` exactly once per case and captures stdout, stderr, and its exit code so it measures the actual CLI contract, including exit 1 for invalid input and exit 2 for service failures. Unit tests use fake transports through the CLI's injectable transport boundary; the harness's production run uses the configured Gemini client. Commit `evidence/eval-results.json` with model name, settings, per-case results, and overall outcome, never the API key. Update only the Git-root `README.md` for documentation: cover both assignment parts and add the Part-1B run and validation commands. No additional architectural layers or persistence are needed.

## Complexity Tracking

No constitution violations; no complexity exceptions.
