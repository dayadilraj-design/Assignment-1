# Prompts used (Part 1A)

Tools: GitHub Spec Kit with GitHub Copilot (Agent mode) in VS Code for the /speckit-* steps. Claude (chat assistant) was used for guidance, review feedback and drafting the harness script; I reviewed and decided each change.

## 1. /speckit-constitution

```
Establish the constitution for a Smart Todo CLI application:
- Python 3.12; runtime uses only the standard library.
- Deterministic behaviour: the same command and the same JSON file always produce the same output and exit code.
- Code quality: `ruff check src tests` reports zero errors.
- Security: `bandit -r src` reports zero medium or high findings; no secrets in code; no eval, exec, pickle or shell=True; validate all user input.
- Testing: pytest. Every acceptance criterion (AC-xx) has at least one test that references its ID. Tests use exact assertions; broad assertions are forbidden.
- A harness runs lint, security and tests; all gates must pass before acceptance.
- The coding agent must never edit, delete, skip or weaken tests or the harness, must not weaken acceptance criteria, must not disable lint or security rules, and must not commit secrets.
- Repair policy: at most 2 automated repair attempts per set of harness failures; the human records results in evidence/harness-log.md.
- Specification changes are made only through the Spec Kit artifacts, with change history kept.
- Prefer simple, maintainable solutions.
Identify measurable quality standards.
```

Manual review edit (by me): constitution v1.1.0 -> v1.2.0. Added a rule to preserve the first generated implementation (tag 1A-initial-generation) and a ban on `# noqa` / `# nosec` suppression comments; set the ratification date.

## 2. /speckit-specify

```
Build a Smart Todo CLI for a single user.
Features: add, list, edit and delete tasks. Each task has an id, title, priority (low, medium, high), tags, and status (todo, doing, done).
Allowed status transitions only: todo->doing, doing->done, doing->todo. Any other transition must be rejected.
Filter the task list by tag. List sorted by priority (high first) with a deterministic tie-break.
Persist all tasks in a local JSON file.
Exit codes: 0 on success; 1 on validation error, illegal transition, or task not found.
Write user stories, functional and non-functional requirements, and numbered binary acceptance criteria (AC-01, AC-02, ...) in Given/When/Then form with exact expected outcomes and exit codes. List assumptions and open questions. Do not describe the implementation.
```

## 3. /speckit-clarify

```
Focus on these ambiguities that block exact, binary tests:
1. Exact stdout format for add, list, edit, status and delete.
2. Behaviour and exit code when the task data file is malformed or unreadable.
3. Whether status changes use a separate command, and what happens for an unknown status value.
4. How NFR-003 (10,000 tasks within 2 seconds) is defined and verified, including the reference environment.
5. How tests can use a temporary data file instead of the default one.
6. An explicitly empty tag filter.
Record each decision in spec.md and add or update acceptance criteria (AC-xx) accordingly.
```

Answers I chose (from Copilot's questions):
- Stdout format: Option A, compact JSON with stable key order.
- Malformed/unreadable data file: Option A, stderr, exit 1, file untouched.
- Status changes: Option A, dedicated `status` command; unknown value is a validation error.
- Performance: Option B, developer's machine, median of five runs <= 2 seconds.
- Temporary data file: Option A, `--data-file <path>`.
- Empty tag filter: validation error, exit 1.

My own notes on what I found and why I chose these:
(Co-Pilot suggested me following "Next Actions
No critical issues block /speckit-implement. Consider clarifying T010’s wording first. Suggested replacement: “include all tasks or only tasks containing the exact requested tag.” No files were modified."

So I gave Agent this command "In tasks.md, change T010's wording to: "include all tasks or only tasks containing the exact requested tag". Change nothing else." )

## 4. /speckit-plan

```
Technology: Python 3.12, standard library only at runtime (argparse for the CLI, json for storage). Tests: pytest. Lint: ruff. Security: bandit.

Project structure: src/todo/ (package with __main__.py, cli.py, models.py, storage.py, service.py) and tests/. Tests call the CLI as a black-box subprocess: python -m todo, with PYTHONPATH=src, and use pytest's tmp_path for the data file.

CLI interface (fix exactly):
- python -m todo [--data-file PATH] add TITLE [--priority low|medium|high] [--tag TAG ...]
- python -m todo [--data-file PATH] list [--tag TAG]
- python -m todo [--data-file PATH] edit ID [--title TITLE] [--priority P] [--tag TAG ...] [--clear-tags]
- python -m todo [--data-file PATH] status ID STATUS
- python -m todo [--data-file PATH] delete ID
Default data file: todo.json in the current working directory.
--tag is repeatable. On edit, giving --tag replaces the whole tag set; --clear-tags empties it.

Describe the architecture, data model, JSON file format, exit-code and error-handling design, the output contract from the spec, and a test strategy that maps every AC-xx to at least one test, including failure cases and the 10,000-task performance test. Explain key decisions and confirm that the plan complies with the constitution and spec.
```

## 4b. Spec/plan fix after reviewing plan.md

```
Make these specification changes through the Spec Kit artifacts, keeping a change history:
1. In spec.md add AC-22: Given an existing task, when the user runs edit with no edit options, or with both --tag and --clear-tags, then the CLI reports a validation error, changes no task data, and exits 1. Update Functional Requirements and any "total acceptance criteria" counts (for example in Success Criteria) to match.
2. In plan.md remove the sentence about repeated list tags acting as an any-match filter; list accepts a single optional --tag.
3. In plan.md change the edit-with-no-options decision from valid no-op to validation error (per AC-22), and add AC-22 to the test strategy table as test_ac22_edit_without_changes_or_conflicting_tag_flags_rejected.
Do not change any other behaviour.
```

Why I made this change (my own words):
(write 2-3 sentences: the plan added behaviour the spec did not approve, e.g. any-match list filter and edit no-op)

## 5. /speckit-tasks

```
Generate tasks for the src/todo/ implementation only: project setup, data model, JSON storage, service logic, CLI commands, validation and error handling, exit codes and the output contract.
Do NOT generate tasks that write or modify tests/ or .harness/. Those are written by the human before implementation and must not be changed by the coding agent.
Reference the relevant FR, AC or NFR IDs in each task.
```

## 6. /speckit-analyze

```
/speckit-analyze
```

Result: no critical issues; suggested clarifying T010's wording ("tasks containing any exact requested tag" -> "the exact requested tag"). No files were modified by analyze.

## 6b. Fix after analyze (T010 wording)

```
In tasks.md, change T010's wording to: "include all tasks or only tasks containing the exact requested tag". Change nothing else.
```

My notes on what analyze found and what I changed:
(write 2-3 sentences here in your own words)

## 7. Harness (written before implementation)

- `.harness/run_harness.py` and `pytest.ini` were drafted with AI assistance (Claude) and reviewed by me. They run three gates: `ruff check src tests`, `bandit -r src -ll -q`, `pytest tests -q`, and write structured results under `evidence/harness-results/`.
- Tests under `tests/` are derived from spec.md (AC-01 to AC-22) and the plan's AC-to-test table, drafted with AI assistance and reviewed by me against the spec.

the tests and harness were drafted with Claude’s help and reviewed by me (Dilraj).