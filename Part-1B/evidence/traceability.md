# Evaluation traceability (Part 1B)

Drafted with AI assistance (Claude) and reviewed by me against `spec.md`. The cases in `evals/dataset.json` were written from the specification (task T008). The dataset is locked and has no field linking a case to a requirement, so this separate file records the mapping.

Every result-producing case is also checked by the schema layer (FR-006, FR-007, FR-008) and by the four semantic checks in FR-015 (status, action, exact `remind_at`, title keywords). The table lists what is specific to each case.

| Case id | Category | Specification requirement tested | Invariant / property checked |
|---|---|---|---|
| normal-01-explicit-date | normal | FR-001, FR-009 | `ok` create has a title and a `remind_at` strictly after `--now` |
| normal-02-relative-hours | normal | FR-002, FR-009 | "in 2 hours" resolves from `--now`, not the system clock |
| normal-03-reschedule | normal | FR-002, FR-009, FR-012a | reschedule has a title and a later time; recurrence is `none` |
| normal-04-snooze | normal | FR-002, FR-009, FR-012a | snooze has a title and a later time; recurrence is `none` |
| normal-05-cancel | normal | FR-009, FR-012a | cancel has a non-empty title and null `remind_at`; recurrence `none` |
| normal-06-daily-recurrence | normal | FR-007, FR-012a | recurrence is `daily`; `remind_at` is the first occurrence |
| normal-07-next-monday | normal | FR-002 | "next <weekday>" is the first such weekday strictly after the `--now` date (Monday reference date) |
| boundary-01-midnight | boundary | FR-002, SC-002 | relative date crossing midnight resolves from `--now` |
| boundary-02-month-end | boundary | FR-002, SC-002 | relative date crossing month end resolves from `--now` |
| boundary-03-year-end | boundary | FR-002, SC-002 | relative date crossing year end resolves from `--now` |
| ambiguous-01-tonight | ambiguous | FR-012 | vague time of day uses the fixed default time |
| ambiguous-02-this-evening | ambiguous | FR-012 | vague time of day uses the fixed default time |
| ambiguous-03-later | ambiguous | FR-010, FR-012 | "later" with no time leads to clarification, not a guess |
| missing-information-01-no-date | missing_information | FR-010, FR-012, SC-003 | missing date/time leads to `needs_clarification`, action `none`, question ends in `?` |
| missing-information-02-reschedule-no-time | missing_information | FR-010, FR-012, SC-003 | reschedule with no new time leads to clarification |
| malformed-01-empty | malformed | FR-001, FR-013, FR-014, FR-016 | exit 1, empty stdout, safe stderr diagnostic, model not called |
| malformed-02-gibberish | malformed | FR-010, FR-012 | non-empty gibberish leads to `needs_clarification` |
| adversarial-01-instruction-override | adversarial | FR-011, FR-012, SC-003 | instruction override is refused; no executable reminder |
| adversarial-02-unrelated-poem | adversarial | FR-011, FR-012, SC-003 | unrelated request is refused; no executable reminder |

Run-level requirements checked by the harness for all cases: FR-015 (every case runs once through `cli.main`), FR-016 (scoring 0.3 / 0.4 / 0.3), FR-017 (pass rule and `ERROR` / `INCONCLUSIVE`), FR-018 (evidence file without the key).