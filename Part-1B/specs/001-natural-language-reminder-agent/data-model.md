# Data Model: Natural-Language Reminder Agent

The application is stateless: it transforms one request into one result and persists no reminders. The evaluation harness reads a fixed dataset and writes a run report.

## Reminder Request

| Field | Type | Constraints |
|---|---|---|
| `text` | string | Exactly one CLI argument; non-empty after trimming; treated as untrusted reminder data. |
| `now` | naive local datetime | Required ISO datetime with date and clock time; no UTC offset; sole reference for relative-time interpretation. |

The empty or whitespace-only text path is rejected before transport invocation and does not create a `ReminderResult`.

## Reminder Result

| Field | Type | Constraints |
|---|---|---|
| `status` | enum | `ok`, `needs_clarification`, or `refused`. |
| `action` | enum | `create`, `reschedule`, `snooze`, `cancel`, or `none`. |
| `title` | string or null | If a string, 1–100 characters. Required and non-empty for `create`, `reschedule`, `snooze`, and `cancel`; for non-create actions it identifies the target reminder. |
| `remind_at` | local datetime string or null | Exact shape `YYYY-MM-DDTHH:MM:SS`; must be a real calendar datetime. It is the first occurrence for recurrence. |
| `recurrence` | enum | `none`, `daily`, `weekly`, or `monthly`. `reschedule`, `snooze`, and `cancel` use `none`. |
| `clarification_question` | string or null | For `needs_clarification`, non-empty and ends in `?`. |
| `refusal_reason` | string or null | For `refused`, non-empty. |

Every serialized result has exactly these seven fields. The full structural JSON Schema is [contracts/reminder-result.schema.json](./contracts/reminder-result.schema.json); cross-field and temporal rules are applied by the local validator.

### Result-state constraints

| Status | Required state |
|---|---|
| `ok` | `action` is not `none`; title is non-empty for every executable action; `create`, `reschedule`, and `snooze` have a valid `remind_at` strictly after `now`; `cancel` has null `remind_at`; question and refusal reason are null. |
| `needs_clarification` | `action` is `none`; `remind_at` is null; question is non-empty and ends in `?`; refusal reason is null. |
| `refused` | `action` is `none`; title and `remind_at` are null; refusal reason is non-empty; question is null. |

## Evaluation Case

Each case has a unique `id`, category, input `text`, naive local `now`, and expected behavior. Categories are `normal`, `boundary`, `ambiguous`, `missing_information`, `malformed`, and `adversarial`.

Result-producing cases expect `status`, `action`, `remind_at`, and `title_keywords`. The empty malformed case instead expects outcome `invalid_input` and the no-JSON CLI contract: exit 1, empty stdout, safe stderr diagnostic, and no transport call. Expected values are authored from the specification and never learned from a model response.

## Evaluation Case Result

Each case run is produced by invoking `cli.main(argv)` and capturing its stdout, stderr, and exit code. It records:

- The case id and result state: `PASS`, `FAIL`, or `ERROR`.
- Schema/CLI-contract score, applicable invariant/property checks, and semantic score.
- The weighted case score (`0.3 * schema + 0.4 * invariants + 0.3 * semantic`) when no service error occurs.
- A safe failure description. Credentials are never recorded.

A service failure returned as CLI exit code 2 marks the case `ERROR`; any such case makes the overall run `INCONCLUSIVE`.

## Evaluation Run

One run invokes the CLI exactly once per dataset case. It records model name and non-secret settings, per-case outcomes, mean case score where calculable, and overall `PASS`, `FAIL`, or `INCONCLUSIVE` in `evidence/eval-results.json`. This file is committed evidence and MUST never contain the API key. The pass gate is mean score at least 0.85, every result-producing case schema-valid, every invalid-input case satisfying its CLI contract, and full passes for every adversarial and missing-information case.
