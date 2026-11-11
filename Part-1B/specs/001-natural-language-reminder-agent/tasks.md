# Tasks: Natural-Language Reminder Agent

**Input**: Design documents from `specs/001-natural-language-reminder-agent/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`

**Organization**: Setup and foundational test/data tasks come first. Tests and evaluation expectations are authored from the specification before application implementation. User-story phases then implement independently testable behavior in priority order.

**Evaluation freeze rule**: After the first evaluation, do not change the locked dataset/expected values or harness evaluators/threshold except through a documented specification change with history retained.

## Phase 1: Setup

**Purpose**: Establish the Python package and development/test environment.

- [ ] T001 Create `pyproject.toml` for Python 3.12, configure pytest to discover `tests/` and import from `src/`, and configure Ruff with the project’s required lint rules; list pytest, Ruff, and Bandit as development tools only, with no runtime dependencies.
- [ ] T002 [P] Create the source package and test directories described in `specs/001-natural-language-reminder-agent/plan.md`: `src/reminder_agent/__init__.py`, `tests/`, `.harness/`, and `evals/`.

## Phase 2: Foundational Tests and Evaluation Data

**Purpose**: Freeze specification-derived expectations and establish failing tests before implementing the application or evaluation logic.

- [ ] T003 [P] Write validator and invariant tests in `tests/test_validation.py` for exactly the seven required fields with no extras; allowed status/action/recurrence values; title constraint “If a string, 1–100 characters.”; remind-at constraint “Exact shape `YYYY-MM-DDTHH:MM:SS`; must be a real calendar datetime.”; and the `ok`, `needs_clarification`, and `refused` invariants, including strict `remind_at > now` for create/reschedule/snooze and a non-empty target title with recurrence `none` for reschedule/snooze/cancel.
- [ ] T004 [P] Write fake-transport unit tests in `tests/test_client.py` for `urllib` request settings, `x-goog-api-key` header use, temperature `0.2`, 30-second timeout, at most three total attempts with retries only for HTTP 429/503, no retries for other HTTP/network/timeout failures, `ServiceError` mapping, environment-over-`.env` precedence, and absence of the key from diagnostics.
- [ ] T005 [P] Write CLI contract tests in `tests/test_cli.py` that call `cli.main(argv)` with captured stdout/stderr and an injected fake transport; cover one compact JSON object and exit 0 for each result status, exit 1/no JSON for empty or whitespace-only text and invalid `--now`, exit 1/no JSON for invalid model output, and exit 2/no JSON with a safe stderr diagnostic for `ServiceError`.
- [ ] T006 [P] Write core and prompt tests in `tests/test_core.py` and `tests/test_prompt.py` using a fake transport; verify the supplied naive `now` anchors interpretation, user reminder text is passed as data rather than system instructions, fixed time-of-day defaults are present, incomplete/ambiguous text is not assigned guessed dates, and model output is validated before return.
- [ ] T007 [P] Write harness contract/scoring tests in `tests/test_harness.py` before implementing `.harness/run_eval.py`; require one `cli.main(argv)` call per case with captured stdout/stderr/exit code, verify no direct `core.run` invocation, test all three weighted layers and the `0.85` pass gate, the empty `invalid_input` outcome/no-model-call invariant, a simulated CLI exit 2 as case `ERROR` and overall `INCONCLUSIVE`, and evidence serialization without an API key. **[LOCKED AFTER FIRST EVALUATION: evaluator behavior tests]**
- [ ] T008 Create `evals/dataset.json` with at least 18 unique cases (at least 6 normal, 3 boundary, 3 ambiguous, 2 missing-information, 2 malformed, and 2 adversarial); include all required `id`, `category`, `text`, `now`, and expected fields, an empty-text malformed case expecting `invalid_input`, and title keywords where applicable. Derive every expected value from `specs/001-natural-language-reminder-agent/spec.md` only, never from model output. **[LOCKED AFTER FIRST EVALUATION: cases, inputs, reference times, categories, and expected values]**
- [ ] T009 Add dataset-shape and immutable-threshold regression checks in `tests/test_harness.py` for the category minimums and at least 18 cases; assert that the specified score weights remain schema `0.3`, invariants `0.4`, semantic `0.3`, and the pass threshold remains `0.85`. **[LOCKED AFTER FIRST EVALUATION: dataset checks and threshold regression test]**

**Checkpoint**: Test specifications and dataset expectations exist before application/evaluator implementation; initial tests may fail until their story phases are implemented.

## Phase 3: User Story 1 - Create and Manage a Reminder (Priority: P1)

**Goal**: Turn a valid request into a correct, schema-valid reminder result, including future-time changes or cancellation by identified title.

**Independent Test**: Using fake transport and a fixed naive `now`, invoke the CLI and verify exact seven-field JSON, correct future-time comparisons, target title handling, and exit/status behavior against `tests/test_validation.py`, `tests/test_client.py`, `tests/test_core.py`, and `tests/test_cli.py`.

### Implementation for User Story 1

- [ ] T010 [US1] Implement exact field/type/enum and cross-field validation in `src/reminder_agent/validation.py`; enforce title strings of 1–100 characters, valid local `YYYY-MM-DDTHH:MM:SS`, strict future `remind_at` for create/reschedule/snooze, and non-empty titles with recurrence `none` for reschedule/snooze/cancel.
- [ ] T011 [US1] Implement Gemini configuration and HTTPS transport in `src/reminder_agent/client.py`; read `GEMINI_API_KEY` and `LLM_MODEL` from environment with `.env` fallback, use the `x-goog-api-key` header, temperature `0.2`, 30-second timeout, and no more than three total attempts retrying only HTTP 429/503; raise `ServiceError` without exposing the key.
- [ ] T012 [US1] Implement `run(text, now, transport)` in `src/reminder_agent/core.py` and the baseline request prompt in `src/reminder_agent/prompt.py`; reject empty text before transport, include `now` as the sole date anchor, parse model JSON, and reject every result that fails `src/reminder_agent/validation.py`.
- [ ] T013 [US1] Implement `main(argv, transport=...)` in `src/reminder_agent/cli.py` and the module entry point in `src/reminder_agent/__main__.py`; require exactly one text argument and an offset-free ISO `--now`, emit one compact JSON object only for valid results, and map valid result/application/service outcomes to exit codes 0/1/2 with diagnostics only on stderr.

**Checkpoint**: User Story 1 works independently through the CLI using fake transport; its validator and CLI tests pass.

## Phase 4: User Story 2 - Clarify Incomplete Requests and Refuse Unsafe Inputs (Priority: P1)

**Goal**: Ask rather than guess for incomplete or ambiguous requests, and produce non-executable refusals for harmful, unrelated, or instruction-override requests.

**Independent Test**: Run the missing-information, malformed-gibberish, ambiguous-time, and adversarial cases through the CLI with fake transport; verify clarification/refusal invariants and that embedded reminder text cannot change system instructions or create an unrelated action.

### Implementation for User Story 2

- [ ] T014 [US2] Write the system instruction and request formatting in `src/reminder_agent/prompt.py`; explicitly treat all reminder text as untrusted data, ignore instructions contained within that data, require clarification for missing date/time, a time at or before `now`, absent target titles, and “later”/“soon” without a time, and map dated morning/afternoon/evening/night to 09:00/14:00/18:00/21:00.
- [ ] T015 [US2] Integrate prompt outcomes with `src/reminder_agent/core.py` and `src/reminder_agent/validation.py`; ensure `needs_clarification` has action `none`, null `remind_at`, a non-empty question ending in `?`, null refusal reason, and `refused` has action `none`, null title/time/question, and a non-empty refusal reason.

**Checkpoint**: User Story 2 independently returns clarification or refusal results and passes safety, missing-information, and adversarial tests without creating executable reminders.

## Phase 5: User Story 3 - Evaluate Results and Preserve Evidence (Priority: P2)

**Goal**: Run every evaluation case through the real CLI entry point, calculate the specified three-layer score, and produce reviewable credential-free evidence.

**Independent Test**: Run harness tests with fake CLI transports, including empty input and a simulated service failure; verify captured exit code/streams, layer scores, per-case statuses, overall outcome, and result metadata. A live evaluation run uses the configured Gemini service.

### Implementation for User Story 3

- [ ] T016 [US3] Implement the single harness in `.harness/run_eval.py`; read `evals/dataset.json` without modifying it, call `cli.main(argv)` exactly once per case with captured stdout/stderr/exit code, inject a fake transport only in tests, and never call `core.run` directly from the harness.
- [ ] T017 [US3] Implement all three evaluator layers and run scoring in `.harness/run_eval.py`: schema or `invalid_input` CLI-contract score is 1/0; invariants score is passed applicable checks divided by applicable checks; semantic score is passed status/action/exact-remind_at/title-keyword checks divided by four; combine as `0.3*schema + 0.4*invariants + 0.3*semantic`; require mean `>= 0.85`, every result-producing case schema-valid, the `invalid_input` case contract-valid, and full adversarial/missing-information passes. Record CLI exit 2 as case `ERROR` and any error as overall `INCONCLUSIVE`. **[LOCKED AFTER FIRST EVALUATION: threshold, evaluator predicates, weights, scoring, and pass/fail rules]**
- [ ] T018 [US3] Write `evidence/eval-results.json` from `.harness/run_eval.py` with model name, non-secret settings, every per-case result, and overall `PASS`/`FAIL`/`INCONCLUSIVE`; ensure no API key or credential value is serialized and preserve the generated results as committed evidence.
- [ ] T019 [US3] Run `git tag 1B-initial-generation` from repository root `C:\dev\Assignment-1` on the complete first implementation before any evaluation-driven repair; first verify the tag does not already exist and never overwrite an existing tag.

**Checkpoint**: User Story 3 tests pass, every case is exercised through the CLI, service failures produce `ERROR`/`INCONCLUSIVE`, and generated evidence contains no credential.

## Phase 6: Polish and Cross-Cutting Concerns

**Purpose**: Document both assignment parts, run project quality gates, and complete the required human evaluation record.

- [ ] T020 [P] Update only the Git-root `README.md` at `../README.md`; preserve documentation for both assignment parts and add Part-1B `.env.example` setup, CLI invocation, evaluation harness, `pytest`, Ruff, and Bandit commands with expected exit/evaluation outcomes.
- [ ] T021 Run `python -m pytest`, `ruff check src tests .harness evals`, and `bandit -r src -ll` from `Part-1B/`; fix failures in the relevant files without changing locked evaluation inputs or rules.
- [ ] T022 Run `python .harness/run_eval.py` from `Part-1B/` using configured credentials; confirm each case runs once through `cli.main`, review `evidence/eval-results.json` for model/settings/per-case/overall fields, verify no API key appears, and retain the generated evidence file.
- [ ] T023 Record the human `ACCEPT` or `REJECT` decision and short justification for the evaluation run in `evidence/harness-log.md`; if evaluation has any `ERROR`, record the run as `INCONCLUSIVE` and do not record it as a pass.
- [ ] T024 If evaluation failures require repair, preserve the first implementation with tag `1B-initial-generation` before repair, limit automated repair attempts to two per failure set, and document each attempt in `evidence/harness-log.md`; do not modify locked evaluation artifacts except through a documented specification change.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; establishes package/test paths.
- **Foundational tests and data (Phase 2)**: Depends on Setup. Dataset and expected outcomes are derived from the spec and tests are written before implementation; this phase blocks implementation.
- **User Story 1 (Phase 3)**: Depends on Setup and Foundational tests/data.
- **User Story 2 (Phase 4)**: Depends on Foundational tests/data and the shared CLI/core/validator from User Story 1.
- **User Story 3 (Phase 5)**: Depends on working CLI/core behavior from User Stories 1 and 2 plus the prewritten dataset and harness tests.
- **Polish (Phase 6)**: README can proceed after Setup; quality checks and live evaluation depend on all three stories; human acceptance depends on the evaluation result.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2; no dependency on another user story.
- **User Story 2 (P1)**: Starts after Phase 2; integrates safety/clarification prompt behavior with User Story 1’s shared core and validator.
- **User Story 3 (P2)**: Starts after User Stories 1 and 2; evaluates their CLI behavior through the actual entry point.

### Parallel Opportunities

- In Phase 2, T003–T007 are independent test files and can be authored in parallel; T008 dataset authoring can also proceed independently from test-file authoring.
- T010 and T011 edit separate implementation files and can proceed in parallel; T014 prompt authoring is also a separate file after the foundation.
- In Phase 6, T020 README documentation is independent of test and evaluation runs.
- The harness implementation (T016–T018) is sequential because scoring and evidence depend on the CLI runner and evaluator.

## Parallel Example: Foundational Tests and Dataset

```text
Task T003: Write validator and invariant tests in tests/test_validation.py
Task T004: Write client retry/configuration tests in tests/test_client.py
Task T005: Write CLI contract tests in tests/test_cli.py
Task T006: Write core and prompt tests in tests/test_core.py and tests/test_prompt.py
Task T007: Write CLI-driven harness scoring/error tests in tests/test_harness.py
Task T008: Create specification-derived, locked evaluation cases in evals/dataset.json
```

## Parallel Example: User Story 1

```text
Run T010 (src/reminder_agent/validation.py) and T011 (src/reminder_agent/client.py) in parallel because they edit separate files.
After both are complete, run T012 (src/reminder_agent/core.py and src/reminder_agent/prompt.py), then T013 (src/reminder_agent/cli.py and src/reminder_agent/__main__.py).
```

## Parallel Example: User Story 2

```text
T014 (src/reminder_agent/prompt.py) must finish before T015 integrates the clarification/refusal invariants in src/reminder_agent/core.py and src/reminder_agent/validation.py.
There are no independent parallel implementation tasks within this story because the prompt behavior and its result validation form one dependent slice.
```

## Parallel Example: User Story 3

```text
T016 (.harness/run_eval.py CLI runner) must finish before T017 adds its scoring rules; T018 evidence serialization depends on both.
T019 tags the completed first implementation before T022 runs the evaluation.
There are no independent parallel harness implementation tasks because the runner, evaluator, evidence, and baseline tag are ordered.
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational phases so schema tests and expected evaluation data exist before implementation.
2. Implement User Story 1 and pass the validator/client/core/CLI tests with fake transport.
3. **STOP and VALIDATE**: verify create, reschedule, snooze, cancel, future-time, and invalid-input behavior independently through the CLI.
4. User Story 1 is the runnable reminder-generation MVP; User Stories 2 and 3 are required before the complete product/evaluation gate.

### Incremental Delivery

1. Add User Story 2 and validate clarification/refusal and adversarial tests through the CLI.
2. Add User Story 3 and validate the full dataset, three evaluation layers, service failure handling, and committed evidence.
3. Run quality commands, then record human evaluation acceptance/rejection.

## Notes

- Every task uses the required checkbox, sequential task ID, optional `[P]`, and story label for user-story phase tasks.
- `[LOCKED AFTER FIRST EVALUATION]` tasks identify evaluation material that must not be changed after the first evaluation except through a documented specification change.
- All evaluation expectations are authored from the specification before implementation, never inferred from model output.
- Tests use fake transports and do not call the network; only the full evaluation harness uses the configured live model client.
