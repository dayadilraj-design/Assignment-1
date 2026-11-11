<!--
Sync Impact Report
Version change: 1.0.0 -> 1.1.0
Modified principles/sections:
- IV. Credential and Service Boundaries (expanded; title unchanged)
- Quality and Evaluation Workflow (expanded; title unchanged)
Added sections: None.
Removed sections: None.
Follow-up TODOs: None.
-->

# Natural-Language Reminder Agent Constitution

## Core Principles

### I. Standard-Library Runtime
The application MUST run on Python 3.12 and use only the Python standard library at
runtime. Model requests MUST use HTTPS through `urllib`; runtime third-party packages
are prohibited. This keeps deployment and runtime behavior small and reproducible.

### II. Stable, Validated Contract
The application MUST convert unstructured reminder requests into JSON conforming to
the stable schema and allowed values defined by the feature specification. Model
wording may vary, but schema structure, allowed values, and safety rules MUST NOT.
Every model result MUST be validated before it is returned or acted upon; invalid
results MUST NOT be treated as successful reminders.

### III. Safe Clarification and Refusal
When mandatory information is missing, the application MUST request clarification
instead of guessing. Malicious, unrelated, or instruction-override requests MUST NOT
produce an executable reminder or tool action. Such inputs MUST be handled as
non-executable outcomes permitted by the specified schema.

### IV. Credential and Service Boundaries
The API key MUST be read only from `GEMINI_API_KEY` or a local `.env` file that is
git-ignored. It MUST never be hard-coded, logged, printed, or committed. The model
name MUST come from `LLM_MODEL`. Model calls MUST use a fixed temperature of `0.2`,
a 30-second timeout, and no more than three total attempts, retrying only temporary
HTTP 429 and 503 responses. Service or network failures MUST be reported separately
from application or evaluation failures. The evaluation harness MUST report each
such failure, including a timeout, network error, or HTTP 429/503 response after the
allowed attempts, as a separate `ERROR` status for that case. Such a case MUST NOT
count as an application `FAIL` or `PASS`. If any such service error occurs, the run
result MUST clearly state that it is inconclusive.

The coding agent MUST NOT read, print, or modify the `.env` file or any credential
value. It MAY create or edit `.env.example` only with placeholders and no
credential values.

### V. Simplicity and Safe Implementation
Implementations MUST prefer the simplest maintainable design that satisfies the
specified contract. Dynamic execution and unsafe serialization mechanisms MUST NOT
be introduced. In particular, `eval`, `exec`, `pickle`, and `shell=True` are
prohibited; `# noqa` and `# nosec` suppressions are also prohibited.

## Operational Constraints
The project MUST target Python 3.12. The application runtime MUST use only the
standard library, including `urllib` for HTTPS model requests. The local `.env`
file, when used, MUST be excluded by `.gitignore`. Credentials MUST NOT appear in
source control, terminal output, or application logs.

Model generation settings MUST remain fixed at temperature `0.2`, timeout 30
seconds, and at most three total attempts for HTTP 429 or 503 responses. Other
failures MUST NOT be retried under this policy. Missing required request data MUST
lead to clarification; untrusted model output MUST be validated against the
specification before it is accepted. Refused or unrelated inputs MUST have no
executable reminder or tool-action effect.

## Quality and Evaluation Workflow
The quality gate MUST pass all of these checks:

- `ruff check src tests .harness evals` reports zero errors.
- `bandit -r src -ll` reports zero medium or high findings.
- Source contains no `eval`, `exec`, `pickle`, or `shell=True`, and no `# noqa` or
  `# nosec` suppressions.

A single evaluation harness MUST run the entire evaluation dataset through all
three layers: schema validation, invariant and property checks, and semantic
quality scoring. It MUST produce one PASS or FAIL against a threshold declared in
the feature specification before the final evaluation begins. Evaluation cases,
expected results, the threshold, guardrails, and harness evaluators MUST NOT be
removed, edited, lowered, or disabled by the coding agent. Changes are permitted
only through a documented specification change made using the Spec Kit artifacts,
with change history retained.

The evaluation dataset MUST contain at least 15 cases covering normal, boundary,
ambiguous, missing-information, malformed, and adversarial inputs. If a service
error occurs, the affected case MUST receive a separate `ERROR` status and the run
result MUST state clearly that the evaluation is inconclusive, not a PASS or FAIL.
Each evaluation run MUST end with a human `ACCEPT` or `REJECT` decision. The
decision and a short justification MUST be recorded in `evidence/harness-log.md`.

For each set of evaluation failures, automated repair MUST be limited to at most
two attempts. The first generated implementation MUST be preserved with the
`1B-initial-generation` tag before any repair. A human MUST record evaluation and
repair results in `evidence/harness-log.md`.

## Governance
This constitution governs implementation and evaluation practices for the
Natural-Language Reminder Agent. Amendments MUST be made through the Spec Kit
artifacts, with the change history retained. An amendment MUST state its rationale
and identify any affected specifications, evaluation cases, expected results,
thresholds, or guardrails.

Version numbers MUST follow semantic versioning: MAJOR for backward-incompatible
governance or principle changes, MINOR for added principles or materially expanded
guidance, and PATCH for clarifications and non-semantic refinements. Compliance
MUST be reviewed when specifications or implementation change and before final
evaluation; the named quality and evaluation gates above are mandatory.

**Version**: 1.1.0 | **Ratified**: 2026-11-11 | **Last Amended**: 2026-11-11
