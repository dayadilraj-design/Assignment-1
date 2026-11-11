# Prompts used (Part 1A)

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