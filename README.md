# Assignment-1

This repository contains two Python command-line projects.

## Part 1A: TODO CLI

Part 1A is a JSON-backed TODO application with commands to add, list, edit,
change the status of, and delete tasks. From the repository root, run:

```powershell
Set-Location .\Part-1A
python -m pip install pytest ruff bandit
$env:PYTHONPATH = "src"
python -m todo --help
python -m pytest
python .harness\run_harness.py
```

The Part 1A harness runs its lint, security, and test gates and returns exit
code 0 only when all gates pass.

## Part 1B: Natural-Language Reminder Agent

Part 1B is a Python 3.12 CLI that converts one reminder request into a
validated JSON result using Gemini. Run commands from `Part-1B`:

```powershell
Set-Location ..\Part-1B
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` and `LLM_MODEL` in `.env` or the process environment.
The local `.env` is ignored by Git; do not commit or print its contents.

Run the CLI with an explicit, offset-free reference datetime:

```powershell
python -m reminder_agent "Remind me tomorrow at 9am to call Sam" --now 2026-11-11T18:00:00
```

Exit code 0 means a valid reminder, clarification, or refusal JSON result was
written to stdout. Exit code 1 indicates invalid input or an application error;
exit code 2 indicates a service/network failure. Error cases do not emit a
result object.

Run the offline tests and quality checks from `Part-1B`:

```powershell
python -m pytest
ruff check src tests .harness evals
bandit -r src -ll
```

Tests use fake transports and do not call the network. The evaluation harness
uses the configured Gemini service and writes per-case results and the overall
`PASS`, `FAIL`, or `INCONCLUSIVE` outcome to
`evidence/eval-results.json`; it never records the API key:

```powershell
python .harness\run_eval.py
```

The evaluation exits 0 for `PASS`, 1 for `FAIL`, and 2 for `INCONCLUSIVE` when
any case encounters a service failure. A pass requires a mean case score of at
least 0.85, valid result contracts, and full passes for adversarial and
missing-information cases. Record the human evaluation decision separately in
`evidence/harness-log.md`.