# Quickstart: Validate Smart Todo CLI

## Prerequisites

- Python 3.12 (the project virtual environment currently provides Python 3.12.16).
- pytest, ruff, and bandit available in the development environment.
- Run commands from `Part-1A`.

## Run a CLI smoke scenario

In PowerShell:

```powershell
$env:PYTHONPATH = 'src'
$py = '.\.venv\Scripts\python.exe'
& $py -m todo --data-file .\todo.json add 'Review proposal' --priority high --tag work --tag planning
& $py -m todo --data-file .\todo.json list --tag work
& $py -m todo --data-file .\todo.json status 1 doing
& $py -m todo --data-file .\todo.json edit 1 --title 'Review revised proposal'
& $py -m todo --data-file .\todo.json delete 1
```

Each successful invocation exits 0 and prints exactly one compact JSON value plus a newline. Add/edit/status return a complete task; list returns an array; delete returns `{"deleted":1}`. See [the CLI contract](./contracts/cli.md) and [the data model](./data-model.md).

## Run acceptance and quality checks

```powershell
$env:PYTHONPATH = 'src'
$py = '.\.venv\Scripts\python.exe'
& $py -m pytest
& $py -m ruff check src tests
& $py -m bandit -r src
```

Tests invoke `python -m todo` as a black-box subprocess, set `PYTHONPATH=src`, and use pytest `tmp_path` for isolated JSON files. The test names and assertions must reference every AC-01 through AC-21, including invalid input, illegal transitions, missing IDs, malformed/unreadable files, exact stdout and exit codes, and path overrides.

## Run the 10,000-task performance acceptance test

```powershell
$env:PYTHONPATH = 'src'
$py = '.\.venv\Scripts\python.exe'
& $py -m pytest tests\test_cli_performance.py -q
```

Pre-create a valid 10,000-task JSON file outside the timed interval. For both an unfiltered list and a tag-filtered list, time five full CLI subprocess runs from process launch until all stdout is captured; assert the median for each is at most 2 seconds. Use Python 3.12.16 and report the machine profile with the benchmark result: Windows 11 Pro 10.0.22621; Intel Core i7-8550U @ 1.80 GHz; 7.9 GB visible memory. Record actual measured medians and the machine metadata in the harness evidence as required by the constitution.
