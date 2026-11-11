<!--
Sync Impact Report
   Version change: 1.1.0 -> 1.2.0 (minor: added first-generation preservation and suppression-comment rules)
Modified principles:
  I. Requirements and Correctness -> I. Python Runtime and Dependencies
  II. Focused and Simple Changes -> II. Deterministic CLI Behavior
  III. Verifiable Quality -> III. Input Security
  IV. Clarity and Maintainability -> IV. Acceptance-Test Traceability
  V. Safe and Reproducible Work -> V. Quality Gates and Agent Integrity
Added sections: None.
Removed sections: None.
Follow-up TODOs: Record the original adoption date upon formal ratification.
-->

# Smart Todo CLI Constitution

## Core Principles

### I. Python Runtime and Dependencies
The application MUST run on Python 3.12 and use only the Python standard library at runtime.
Development and test tools MAY be used outside the runtime. This keeps the deployed CLI
lightweight and makes its runtime dependencies reproducible.

### II. Deterministic CLI Behavior
Given the same command, arguments, and JSON input file contents, the CLI MUST produce the same
observable output and exit code. Output MUST NOT vary because of current time, randomness, or
unordered collection iteration. Tests MUST verify deterministic behavior for applicable commands.

### III. Input Security
The application MUST validate all user input and MUST NOT contain secrets. Source code MUST NOT
use `eval`, `exec`, `pickle`, or `shell=True`. `bandit -r src` MUST report zero medium- or
high-severity findings. These requirements reduce injection, unsafe deserialization, and secret
exposure risks.

### IV. Acceptance-Test Traceability
The project MUST use pytest. Every acceptance criterion identified as `AC-xx` MUST be referenced
by at least one test. Tests MUST use exact assertions for expected values, output, and errors;
broad assertions that establish only truthiness, non-emptiness, or a general type MUST NOT be the
sole verification of an acceptance criterion.

### V. Quality Gates and Agent Integrity
`ruff check src tests` MUST report zero errors. The harness MUST run lint, security, and tests, and
all gates MUST pass before acceptance. The coding agent MUST NOT edit, delete, skip, weaken, or
bypass tests or the harness; weaken acceptance criteria; disable lint or security rules; or commit
secrets. This preserves independent, enforceable evidence of correctness.

## Additional Constraints

Solutions MUST prefer simple, maintainable designs and MUST avoid unnecessary dependencies,
abstractions, and behavior. Python runtime dependencies are restricted to the standard library.
Any exception to a constitutional requirement requires explicit approval through the amendment
process.

## Development Workflow

Before implementation, contributors MUST inspect the applicable Spec Kit artifacts and repository
conventions. Changes to specifications MUST be made through Spec Kit artifacts, with change
history retained. A human MUST record harness run results in `evidence/harness-log.md`.

For each set of harness failures, automated repair attempts MUST be limited to two. After the
second unsuccessful attempt, the coding agent MUST stop automated repairs and report the remaining
failures for human review. Acceptance requires successful completion of pytest,
`ruff check src tests`, and `bandit -r src` with no medium- or high-severity findings. Each
applicable `AC-xx` MUST have a test that references its ID and uses exact assertions.

The first generated implementation MUST be committed, tagged `1A-initial-generation`, and copied to
`evidence/initial-generation/` before any harness-driven correction. Harness result files MUST NOT be
edited manually. `# noqa` and `# nosec` suppression comments MUST NOT be used unless approved through
the amendment process.

## Governance

This constitution defines the project's governance requirements. An amendment MUST include a
reason, identify its impact on existing principles or work, and be approved by the repository
owner before adoption. Specification changes MUST be made only through Spec Kit artifacts and
their change history MUST be retained. Changes to this constitution MUST update its version and
last-amended date.

Versioning follows semantic versioning: MAJOR for backward-incompatible removal or redefinition of
a principle, MINOR for a new principle or materially expanded guidance, and PATCH for
clarifications or non-semantic refinements. Reviews MUST verify compliance with this constitution
and require an explicitly documented, approved exception for any deviation.

**Version**: 1.2.0 | **Ratified**: 2026-11-11 | **Last Amended**: 2026-11-11
