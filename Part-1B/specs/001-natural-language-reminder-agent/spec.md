# Feature Specification: Natural-Language Reminder Agent

**Feature Branch**: Not created (no branch hook is configured)

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: Build a Python 3.12 command line tool that converts one unstructured reminder request into one structured JSON result using a Gemini model, with required relative-time handling, safe clarification and refusal, response validation, and a fixed evaluation gate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a reminder from a natural-language request (Priority: P1)

A user submits one reminder request and a reference date and time. The agent returns one structured result that represents the requested reminder, resolving relative dates from the supplied reference time.

**Why this priority**: Creating a correctly timed reminder is the primary value of the agent.

**Independent Test**: Submit a request with an explicit future date and time, then submit requests using relative dates with a fixed reference time; verify that each produces one valid result with the intended action, title, and time.

**Acceptance Scenarios**:

1. **Given** a well-formed request to create a reminder with a future date and time, **When** the user supplies the request and a valid reference time, **Then** the agent returns one compact JSON object with status `ok`, action `create`, a non-empty title, and the intended future reminder time.
2. **Given** a request such as “tomorrow at 9am” and a supplied reference time, **When** the request is processed, **Then** the reminder time is calculated from that reference time and not from the machine’s current time.
3. **Given** a request to reschedule or snooze an identified reminder to a future time, **When** the request is processed, **Then** the result identifies the requested action and a reminder time later than the reference time.
4. **Given** a request to cancel an identifiable reminder, **When** the request is processed, **Then** the result represents cancellation without inventing a reminder time.

---

### User Story 2 - Clarify incomplete requests and refuse unsafe or out-of-scope requests (Priority: P1)

A user receives a clear question when information needed for a reminder is missing, and receives a non-executable refusal when the request is harmful, unrelated, or attempts to override the agent’s instructions.

**Why this priority**: Avoiding guessed dates and unsafe or unrelated actions is essential to user trust.

**Independent Test**: Submit incomplete, ambiguous, malformed, unrelated, harmful, and instruction-override requests; verify clarification or refusal outcomes and ensure none produces an executable reminder.

**Acceptance Scenarios**:

1. **Given** a request to create or change a reminder without a required date or time, **When** it is processed, **Then** the agent returns `needs_clarification`, action `none`, a non-empty question ending in `?`, and no reminder time.
2. **Given** a request that is harmful, unrelated, or tries to override instructions, **When** it is processed, **Then** the agent returns `refused`, action `none`, a non-empty refusal reason, and no title or reminder time.
3. **Given** a harmless reminder whose text contains quoted or embedded instructions, **When** it is processed, **Then** those instructions are treated as reminder data and do not change the agent’s governing instructions or cause unrelated actions.

---

### User Story 3 - Evaluate behavior and review evidence safely (Priority: P2)

A project maintainer runs the complete evaluation dataset and receives per-case results and an overall outcome that distinguishes evaluation failures from unavailable model service.

**Why this priority**: A repeatable, transparent quality gate is necessary to verify the strict schema, safety behavior, and semantic accuracy.

**Independent Test**: Run the harness across every dataset case, including a simulated service failure; verify all three evaluation layers, scores, case statuses, overall outcome, and that evidence contains no API key.

**Acceptance Scenarios**:

1. **Given** a dataset containing at least 18 cases across all required categories, **When** an evaluation is run, **Then** every case is checked for schema validity, invariants and properties, and semantic agreement with its expected result.
2. **Given** a case with a service failure, **When** the evaluation is run, **Then** that case is reported as `ERROR` and the overall run is `INCONCLUSIVE`, not `PASS` or `FAIL`.
3. **Given** an evaluation run completes, **When** its evidence is written, **Then** it includes the model name and settings and excludes the API key.

### Edge Cases

- An empty or gibberish request is malformed and must not result in a guessed executable reminder.
- A missing date or time for a date/time-dependent action must lead to clarification.
- A requested time equal to or earlier than the supplied reference time is not a valid future reminder time.
- Relative dates that cross midnight, the end of a month, or the end of a year must resolve to the correct date.
- An invalid reference datetime or invalid command-line input must produce an application error and no result object.
- A model response with missing, extra, malformed, or inconsistent fields must be rejected as an application error.
- Temporary service unavailability, exhausted retryable responses, and network timeouts must not produce a result object.
- Evaluation cases must cover adversarial input and missing information, and these cases must pass fully for an overall pass.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST accept exactly one unstructured reminder request per command-line invocation and require a valid ISO datetime as `--now`.
- **FR-002**: The application MUST use the supplied `--now` value as the sole reference time for interpreting relative dates and MUST NOT substitute the system clock.
- **FR-003**: The application MUST use a Gemini model to interpret the request and MUST allow the model name to be selected through `LLM_MODEL`.
- **FR-004**: The application MUST accept its API key only from `GEMINI_API_KEY` or a local `.env` file excluded from version control. It MUST NOT log or print the key, and credentials MUST NOT be committed.
- **FR-005**: The application MUST use Python 3.12 and only the Python standard library at runtime; model requests MUST use HTTPS through `urllib`. Model calls MUST use temperature `0.2`, a 30-second timeout, and no more than three total attempts, retrying only HTTP 429 and 503 responses.
- **FR-006**: For a produced result, the command MUST write exactly one compact JSON object to standard output with exactly these fields and no others: `status`, `action`, `title`, `remind_at`, `recurrence`, `clarification_question`, and `refusal_reason`.
- **FR-007**: The result MUST constrain `status` to `ok`, `needs_clarification`, or `refused`; `action` to `create`, `reschedule`, `snooze`, `cancel`, or `none`; and `recurrence` to `none`, `daily`, `weekly`, or `monthly`. `title` MUST be a string of 1–100 characters or null. `remind_at` MUST be an ISO 8601 local datetime in `YYYY-MM-DDTHH:MM:SS` form or null. The question and refusal reason MUST each be a string or null.
- **FR-008**: Before output, the application MUST validate every model response against the exact result schema, allowed values, and status invariants. Invalid responses MUST be application errors, not successful results.
- **FR-009**: An `ok` result MUST have an action other than `none`, a non-empty title for `create`, and a present, valid reminder time strictly later than `--now` for `create`, `reschedule`, and `snooze`. Its clarification question and refusal reason MUST be null.
- **FR-010**: A `needs_clarification` result MUST have action `none`, a null reminder time, a non-empty clarification question ending in `?`, and a null refusal reason.
- **FR-011**: A `refused` result MUST have action `none`, null title and reminder time, a non-empty refusal reason, and a null clarification question.
- **FR-012**: The application MUST request clarification instead of guessing when required date or time information is missing. It MUST refuse harmful, unrelated, or instruction-override requests without producing an executable reminder. Instructions inside reminder text MUST be treated as data and MUST NOT override governing instructions.
- **FR-013**: The command MUST exit with code 0 when it produces a valid result, including clarification and refusal results; code 1 for invalid input or application errors; and code 2 for service/network failures, including timeouts and HTTP 429/503 after the allowed attempts. Service failures MUST be reported to standard error and MUST NOT print a result object to standard output.
- **FR-014**: The evaluation dataset MUST be `evals/dataset.json` and contain at least 18 cases. Each case MUST include an id, category, input text, `now`, and expected fields. It MUST include at least six normal, three boundary, three ambiguous, two missing-information, two malformed, and two adversarial cases.
- **FR-015**: One evaluation harness MUST run every case through schema validation, invariant and property checks, and semantic comparison. Semantic comparison MUST check expected `status`, `action`, and exact `remind_at`, and MUST check that expected title keywords are present.
- **FR-016**: Each evaluation case MUST be scored as 0.3 schema, 0.4 invariants, and 0.3 semantic comparison. The threshold MUST remain fixed at mean case score of at least 0.85 unless changed through a documented specification change.
- **FR-017**: The evaluation run MUST pass only when its mean score is at least 0.85, every case is schema-valid, and every adversarial and missing-information case passes fully. A service failure MUST be reported as `ERROR`, not `FAIL` or `PASS`; any `ERROR` MUST make the overall run `INCONCLUSIVE`.
- **FR-018**: The harness MUST write results to `evidence/eval-results.json`, including the model name and settings but never the API key.

### Key Entities

- **Reminder request**: One unstructured user input, interpreted relative to the required reference datetime.
- **Reminder result**: The seven-field structured outcome describing a created, changed, canceled, clarified, or refused request.
- **Evaluation case**: A categorized input request and reference datetime paired with expected fields for automated comparison.
- **Evaluation result**: Per-case validation layers, scores, and status, together with the overall evaluation outcome and safe run settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of produced results conform to the exact seven-field schema and all applicable structural invariants.
- **SC-002**: 100% of relative-time test cases resolve from the supplied reference time, including midnight, month-end, and year-end boundaries.
- **SC-003**: 100% of adversarial cases are fully refused, and 100% of missing-information cases fully request clarification without producing an executable reminder.
- **SC-004**: An evaluation run passes only at a mean case score of 0.85 or higher, with every case schema-valid and all adversarial and missing-information cases fully passing.
- **SC-005**: For every service failure, no result object is emitted, the case is marked `ERROR`, and the overall evaluation is `INCONCLUSIVE`.
- **SC-006**: No API key appears in committed files, command output, or evaluation evidence.

## Assumptions

- The user supplies a complete ISO datetime with `--now`; its supplied date and clock components govern relative interpretation, and returned reminder datetimes use the requested local datetime representation without an offset.
- The default recurrence for a non-recurring request and for non-executable results is `none`.
- A cancellation request must identify the reminder to cancel; if it does not, the agent asks for clarification rather than guessing.
- The requested threshold and dataset category minimums are binding evaluation requirements; the project constitution’s model-call settings and runtime restrictions also apply.
- Evaluation evidence is generated locally and may include result content, but must never include credential values.
