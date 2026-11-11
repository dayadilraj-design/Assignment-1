# Prompts used (Part 1A)

## 1. /speckit-constitution

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

My own notes on what I found and why I chose these:
(write 3-4 sentences here in your own words)