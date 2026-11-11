# Implementation Plan: Smart Todo CLI

**Branch**: `001-smart-todo-cli` | **Date**: 2026-11-11 | **Spec**: [spec.md](./spec.md)

**Input**: [Feature specification](./spec.md) and the supplied technology, CLI, and test decisions.

## Summary

Build a single-user todo CLI with add, list, edit, status, and delete commands. The CLI uses Python 3.12's standard library (`argparse`, `json`), stores a versioned task collection in a local JSON file, and exposes the exact compact-JSON output and exit-code contract in [contracts/cli.md](./contracts/cli.md). Keep argument parsing/output, task rules, and persistence separated across the specified `cli.py`, `service.py`, `models.py`, and `storage.py` modules. Test every AC through black-box subprocess invocations, including a five-run 10,000-task benchmark.

## Technical Context

**Language/Version**: Python 3.12 (project virtual environment: 3.12.16)

**Primary Dependencies**: Python standard library only at runtime; `argparse` for the CLI and `json` for storage. Development tools: pytest, ruff, bandit.

**Storage**: Local JSON file; default `todo.json` in current working directory, overridden by `--data-file PATH`.

**Testing**: pytest; tests invoke `python -m todo` as a subprocess with `PYTHONPATH=src` and pytest `tmp_path` data files.

**Target Platform**: Local single-user environments running Python 3.12; benchmark reference is the developer's Windows machine.

**Project Type**: Python CLI application.

**Performance Goals**: For a pre-created collection of 10,000 tasks, both unfiltered and tag-filtered full CLI list operations must each have a median duration <= 2 seconds across five runs, including process startup and complete stdout capture.

**Constraints**: Standard-library-only runtime; exact command syntax and compact JSON stdout; failures exit 1 and do not mutate task data; deterministic priority/ID ordering; no `eval`, `exec`, `pickle`, or `shell=True`; `ruff check src tests` clean; `bandit -r src` has no medium/high findings.

**Scale/Scope**: One local user's task file, at least 10,000 tasks for the performance acceptance criterion; no accounts, sync, or collaboration.

## Constitution Check

*GATE: evaluated before research and re-evaluated after design.*

| Principle | Plan compliance |
|---|---|
| I. Python Runtime and Dependencies | Python 3.12 and standard-library-only runtime; pytest/ruff/bandit are development tools only. |
| II. Deterministic CLI Behavior | Fixed JSON key order, stable priority-then-numeric-ID sorting, exact tag membership, and no time/random-based output. |
| III. Input Security | Validate CLI values and stored JSON, use JSON rather than executable serialization, avoid prohibited APIs, and run Bandit. |
| IV. Acceptance-Test Traceability | The AC-to-test matrix below names a pytest test for each AC; tests assert exact values, stdout/stderr, exit codes, and persistence. |
| V. Quality Gates and Agent Integrity | Run pytest, `ruff check src tests`, and `bandit -r src`; retain and do not weaken the test/harness. Honor the required initial-generation commit/tag/copy before any harness-driven correction. |

**Gate result**: PASS. No constitutional exception or unresolved technical clarification is needed. The design keeps scope to one CLI package and its tests.

## Design Decisions

- Follow the user-specified CLI exactly. `--tag` is repeatable; for edit it replaces all tags, while `--clear-tags` empties them. Treat simultaneous `--tag` and `--clear-tags` as invalid. Use argparse choices for enumerated values and normalize parser validation failures to exit code 1 (help remains 0).
- Store `{"version":1,"next_id":N,"tasks":[...]}`. `next_id` is persisted so IDs remain positive, increasing, and never reused after deletion. Reject malformed or unsupported documents before any write.
- Validate and form a complete prospective change before saving. Save to a temporary file in the same directory and atomically replace the original only after serialization succeeds, preserving the previous file on failed operations and avoiding partially written JSON.
- Keep field validation and stable serialization in the model, allowed transitions and ordered/filterable list behavior in the service, disk/JSON responsibilities in storage, and parsing/printing/exit mapping in the CLI.
- Make an edit with no edit options a valid no-op that returns the unchanged complete task. This keeps the optional edit flags useful without inventing a required-field constraint absent from the spec.
- The default and override file paths are resolved relative to the process current working directory when relative. Error wording remains concise and diagnostic; exact phrasing is not mandated, but errors go to stderr.

## Acceptance-Criteria Test Strategy

Every test runs the public module in a fresh subprocess with a temporary data file unless the case specifically verifies the default path. Tests assert stdout exactly (including compact JSON, key order, and newline), stderr/error category, exit code, and unchanged bytes or state on failure where required.

| AC | Black-box pytest coverage |
|---|---|
| AC-01 | `test_ac01_add_uses_defaults_and_persists` |
| AC-02 | `test_ac02_add_stores_supplied_fields` |
| AC-03 | `test_ac03_rejects_invalid_title_priority_and_tags_atomically` (blank/missing title, invalid priority, blank/duplicate tags on add/edit, malformed/non-positive ID) |
| AC-04 | `test_ac04_list_orders_by_priority_then_numeric_id` |
| AC-05 | `test_ac05_tag_filter_is_exact_and_keeps_order` (also cover repeated list tags as an any-match filter) |
| AC-06 | `test_ac06_empty_and_unmatched_lists_succeed` |
| AC-07 | `test_ac07_edit_changes_only_requested_fields` |
| AC-08 | `test_ac08_invalid_edit_is_atomic` (parameterize invalid title, priority, and tags) |
| AC-09 | `test_ac09_todo_to_doing` |
| AC-10 | `test_ac10_doing_to_done` |
| AC-11 | `test_ac11_doing_to_todo` |
| AC-12 | `test_ac12_rejects_all_disallowed_and_same_status_transitions` (verify task data unchanged) |
| AC-13 | `test_ac13_delete_removes_task_from_output_and_file` |
| AC-14 | `test_ac14_edit_delete_and_status_report_missing_id` |
| AC-15 | `test_ac15_changes_survive_separate_cli_invocations` |
| AC-16 | `test_ac16_success_stdout_matches_compact_json_contract` (add/edit/status/list/delete, exact key order and one newline) |
| AC-17 | `test_ac17_malformed_or_unreadable_data_file_is_unchanged` (malformed JSON and an unreadable path, using portable filesystem setup) |
| AC-18 | `test_ac18_unknown_status_is_validation_error` |
| AC-19 | `test_ac19_explicitly_empty_tag_filter_is_rejected` |
| AC-20 | `test_ac20_ten_thousand_task_lists_meet_two_second_median` (pre-create 10,000 records; run each list shape five times, time process launch through complete stdout capture, assert each median <= 2 seconds, record OS/CPU/memory and Python version) |
| AC-21 | `test_ac21_data_file_override_supports_absolute_and_relative_paths` (also verify default `todo.json` is rooted at cwd) |

For AC-17, use malformed bytes/JSON and a path that reliably fails reading on the current platform (for example, a directory at the requested file path); assert stderr, code 1, and that the original file/directory remains unchanged. Do not rely solely on permission bits on Windows. The performance test must run under Python 3.12; the current reference machine is Windows 11 Pro (10.0.22621), Intel Core i7-8550U @ 1.80 GHz, 7.9 GB visible memory.

## Project Structure

### Documentation (this feature)

```text
specs/001-smart-todo-cli/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── cli.md
```

### Source Code and Tests

```text
src/
└── todo/
    ├── __main__.py
    ├── cli.py
    ├── models.py
    ├── storage.py
    └── service.py
tests/
├── conftest.py
├── test_cli.py
└── test_cli_performance.py
```

**Structure Decision**: Use the exact single-package layout supplied by the user. `__main__.py` delegates to `cli.main`; tests exercise only the command-line boundary, not internal functions, to preserve black-box acceptance coverage.

## Constitution Check (Post-Design)

**Gate result**: PASS. The versioned JSON envelope, atomic writes, standard-library runtime, exact output contract, and explicit AC test mapping meet the spec and all five constitutional principles. The benchmark is measurable with the specified Python 3.12 runtime and machine metadata. No extra project, runtime dependency, or unjustified complexity is introduced.

## Complexity Tracking

No constitution violations; no complexity exceptions required.
