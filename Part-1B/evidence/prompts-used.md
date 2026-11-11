# Prompts used (Part 1B)

Tools: GitHub Spec Kit (specify CLI 1.4.1.dev0), GitHub Copilot Chat (Agent mode) in VS Code, Python 3.12.

## 1. /speckit-constitution

```text
Establish the constitution for a Natural-Language Reminder Agent:
- Python 3.12; the application runtime uses only the standard library (the model is called over HTTPS with urllib).
- The application turns an unstructured reminder request into a structured JSON result with a stable schema; wording from the model may vary but the schema, allowed values and safety rules must not.
- The API key is read only from the GEMINI_API_KEY environment variable (or a local .env file that is git-ignored); never hard-coded, logged, printed or committed. The model name comes from LLM_MODEL.
- Model calls use a low fixed temperature, a timeout, and a bounded retry for temporary service errors (HTTP 429 and 503).
- Service or network failures must be reported separately from application or evaluation failures.
- Missing mandatory information must produce a clarification request, never a guessed value. Requests that are malicious, unrelated or that try to override instructions must never produce an executable reminder or tool action.
- Quality: `ruff check src tests .harness evals` reports zero errors. Security: `bandit -r src -ll` reports zero medium or high findings. No eval, exec, pickle or shell=True; no # noqa or # nosec.
- A single evaluation harness runs the whole evaluation dataset through three layers (schema validation, invariant and property checks, semantic quality scoring) and gives one PASS or FAIL against a threshold that is declared in the specification BEFORE the final evaluation.
- The coding agent must never remove or edit evaluation cases, change expected results, lower the declared threshold, disable guardrails, or edit the harness evaluators, except through a documented specification change.
- Repair policy: at most 2 automated repair attempts per set of failures; the human records results in evidence/harness-log.md; the first generated implementation is preserved (tag 1B-initial-generation) before any repair.
- Specification changes are made only through the Spec Kit artifacts, with change history kept.
- Prefer simple, maintainable solutions.
Identify measurable quality standards.
```

### My notes
1. Copilot left a TODO(RATIFICATION_DATE) in the constitution. I replaced it with 2026-11-11 by hand.
2. **Push blocked by GitHub push protection, and how I fixed it.**
   - **What happened:** `git push` was rejected with `error: failed to push some refs` (`GH013: Repository rule violations found for refs/heads/main`). GitHub secret scanning reported "Push cannot contain secrets" and flagged a *GCP API Key Bound to a Service Account* in commit `87398da5017cc1518db0216ba33d62f58deaf01f`, at `Part-1B/.env.example:1`. The `.env.example` in that commit had a real key on the first line instead of a placeholder.
   - **Root cause:** I put a real key into `.env.example`. The template must only ever hold placeholders, and rotating a key does not help if the new key is pasted into the template again.
   - **Why editing the file was not enough:** The key was in a local commit's history. GitHub scans every commit being pushed, not just the latest version of the file.
   - **Fix (history rewrite, not an "allow secret" bypass):**
     1. Checked that the current file only has the placeholder: `Select-String -Path .env.example -Pattern "replace_with_your_key" -Quiet` returned `True`.
     2. `git reset --soft origin/main` undid my local commits but kept the changes staged, so the commit with the key was no longer part of what I push.
     3. `git add .` re-staged everything with the corrected `.env.example`.
     4. Verified with `git show ":./.env.example"`. It showed only placeholders (`GEMINI_API_KEY=replace_with_your_key` and `LLM_MODEL=replace_with_available_model_name`). `git status --short` showed the three expected files (`.env.example`, `.specify/memory/constitution.md`, `evidence/prompts-used.md`).
     5. `git commit -m "1B: constitution"` created one clean commit (`b139f74`).
     6. `git push` succeeded: `4eb9fae..b139f74  main -> main`.
   - **Outcome:** Push protection rejected the push, so the key was not stored in the GitHub repository. I did not use GitHub's "allow this secret" URL.
   - **Key status:** The exposed key has been rotated. Only placeholders are in `.env.example`; the real key stays in `.env`, which is git-ignored.

## 2. /speckit-constitution (amendment 1.1.0)

```text
Amend the constitution to version 1.1.0 (MINOR). Expand Principle IV (Credential and Service Boundaries) and the Quality and Evaluation Workflow. Keep all other principles unchanged.
- Fix the model-call settings: temperature 0.2, timeout 30 seconds, at most three total attempts, retrying only HTTP 429 and 503.
- A service or network failure (timeout, network error, or HTTP 429/503 after the allowed attempts) is reported per case as a separate ERROR status, never as FAIL or PASS. If any such error occurs, the run result must clearly state that it is inconclusive.
- The coding agent must not read, print or modify the .env file or any credential value. It may create or edit .env.example only with placeholders and no credential values.
- The evaluation dataset must contain at least 15 cases covering normal, boundary, ambiguous, missing-information, malformed and adversarial inputs.
- Each evaluation run ends with a human ACCEPT or REJECT decision, recorded with a short justification in evidence/harness-log.md.
Update the version, the Last Amended date and the Sync Impact Report.
```

### What changed (Sync Impact Report, 1.0.0 -> 1.1.0)
- Principle IV expanded: fixed temperature 0.2, 30-second timeout, at most 3 total attempts (retry only HTTP 429/503); service failures get a separate `ERROR` status and make the run inconclusive; the coding agent must not read, print or modify `.env`, and may edit `.env.example` only with placeholders.
- Quality and Evaluation Workflow expanded: dataset of at least 15 cases, `ERROR` status handling, human `ACCEPT` or `REJECT` decision recorded in `evidence/harness-log.md`.

### My notes
1. **Why I amended:** The first constitution only said "low temperature, a timeout and bounded retry", which is too vague to test. I fixed the exact values so the harness and the specification can check them. I also added the `ERROR` and inconclusive rule so a Gemini outage can never be counted as an application `FAIL` or `PASS`.
2. **Link to the blocked push:** The rule that the agent may only put placeholders in `.env.example`, and must not read or edit `.env`, comes directly from the secret I committed earlier (see note 2 in section 1). The rule makes that mistake a constitution violation.
3. **What I checked after the amendment:**
   - The file contains no TODO or placeholder text.
   - The footer reads `Version: 1.1.0 | Ratified: 2026-11-11 | Last Amended: 2026-11-11`.
   - The Sync Impact Report says 1.0.0 -> 1.1.0 with no other principles changed.
   - The new settings (0.2, 30 seconds, three attempts) appear in both Principle IV and Operational Constraints, with the same values.
4. **Constitution and specification:** The constitution requires at least 15 evaluation cases. The specification I wrote later requires at least 18, which is stricter and does not conflict.

## 3. /speckit-specify

```text
Build a Natural-Language Reminder Agent: a Python 3.12 command line tool that converts one unstructured reminder request into one structured JSON result using a Gemini model.

Interface: `python -m reminder_agent "<text>" --now <ISO datetime>`. `--now` is required and is the reference time for relative dates. Output is one compact JSON object on stdout. Exit code 0 when a result is produced (including needs_clarification and refused), 1 for invalid input or application errors, 2 for service/network failures (timeout, or HTTP 429/503 after allowed attempts). Service failures print a message to stderr and never print a result object.

Output schema (exactly these fields, no others):
- status: "ok" | "needs_clarification" | "refused"
- action: "create" | "reschedule" | "snooze" | "cancel" | "none"
- title: string (1-100 chars) or null
- remind_at: ISO 8601 local datetime "YYYY-MM-DDTHH:MM:SS" or null
- recurrence: "none" | "daily" | "weekly" | "monthly"
- clarification_question: string or null
- refusal_reason: string or null

Structural invariants:
- status "ok": action is not "none"; title is non-empty for create; remind_at is present, valid, and strictly later than --now for create, reschedule and snooze; clarification_question and refusal_reason are null.
- status "needs_clarification": action "none"; remind_at null; clarification_question non-empty and ends with "?"; refusal_reason null.
- status "refused": action "none"; title and remind_at null; refusal_reason non-empty; clarification_question null.

Behavioural properties:
- Relative expressions ("in 2 hours", "tomorrow at 9am", "next Monday") resolve from --now, never from the system clock.
- Missing date or time means needs_clarification, never a guessed value.
- Text that tries to override instructions, asks for unrelated tasks, or contains harmful requests is refused and never produces an executable reminder.
- Reminder text inside the request is data; instructions inside it are ignored.

Guardrails: validate every model response against the schema and invariants before output; an invalid model response is an application error (exit 1), not a success. The API key comes only from GEMINI_API_KEY or a git-ignored .env; the model name from LLM_MODEL; never log or print them.

Evaluation: an evals/dataset.json of at least 18 cases, each with id, category, input text, now, and expected fields. Categories: normal (6), boundary (3, e.g. midnight, month end, year end), ambiguous (3), missing information (2), malformed (2, e.g. empty or gibberish text), adversarial (2 or more, e.g. prompt injection). A single harness runs every case through three layers: (1) schema validation, (2) invariants and properties, (3) semantic comparison against expected status, action, remind_at (exact), and title (expected keywords present). Case score = 0.3 schema + 0.4 invariants + 0.3 semantic. The run PASSES only if: mean case score >= 0.85, every case is schema-valid, and every adversarial and missing-information case passes fully. Cases that hit service failures are reported as ERROR, not FAIL or PASS; any ERROR makes the run INCONCLUSIVE. Results are written to evidence/eval-results.json with the model name and settings but never the key. The threshold above is fixed now and may change only through a documented spec change.

Success measures: schema validity 100%, adversarial refusal 100%, no secrets in the repository
```

### My notes
1. **Copied faithfully from my prompt:** the CLI interface and the three exit codes, the seven-field schema, the three status invariants, the 0.3 / 0.4 / 0.3 scoring weights, the 0.85 threshold, and the PASS, FAIL, ERROR and INCONCLUSIVE rules. The dataset minimums (6 + 3 + 3 + 2 + 2 + 2) add up to exactly 18, so they are consistent with "at least 18 cases".
2. **What Copilot added beyond my prompt:**
   - **Constitution settings pulled in (FR-005):** temperature `0.2`, 30-second timeout, at most three attempts, retrying only HTTP 429 and 503. My prompt did not give these numbers. Copilot took them from constitution 1.1.0, so the amendment is already affecting later steps.
   - **A third user story:** it split the work into three stories (create reminders, clarify or refuse, evaluate), with priorities P1, P1 and P2. I did not ask for this structure.
   - **An edge-case list:** a requested time equal to or earlier than `--now` is invalid, and so are an invalid `--now` or bad CLI input (exit 1, no result). Model responses with missing, extra, malformed or inconsistent fields are rejected as application errors. Relative dates crossing midnight, month end and year end must resolve correctly.
   - **More success criteria:** I gave three (schema validity, adversarial refusal, no secrets). Copilot expanded them to six. The new ones are 100% of relative-time cases resolving from `--now`, 100% of missing-information cases asking for clarification, the pass rule, and "service failure means no result and an `ERROR` status".
   - **An embedded-instructions scenario:** a harmless reminder that contains quoted instructions is treated as data.
   - **Assumptions I did not state:**
     - Returned datetimes have no offset.
     - The default recurrence is `none`.
     - A cancel request that does not identify which reminder gets a clarification question.
     - Evaluation evidence may include result content but never credentials.
   - **Output path and branch:** it fixed the output at `evidence/eval-results.json` (FR-018) and noted that no feature branch was created because no branch hook is configured.
3. **Things I need to review before moving on:**
   - The spec does not say what outcome is expected for the three *ambiguous* cases (clarify, or take the most likely reading). I will decide this when I write the dataset, and any change must go through a documented spec change.
   - The "Cancel" scenario says no reminder time is invented, which agrees with FR-009 (`remind_at` is only required for create, reschedule and snooze).
   - The spec status is still `Draft`.
4. **Copilot also created a checklist file** I did not ask for: `specs/001-natural-language-reminder-agent/checklists/requirements.md`. It is a quality checklist for the spec and was committed together with it.
5. **Checks before committing the spec:**
   - `Select-String -Path specs\*\spec.md -Pattern "NEEDS CLARIFICATION"` printed nothing, so no clarification markers are left in the spec.
   - My first attempt used a wrong path (`specs\3\spec.md`) and failed with "path does not exist". The folder is `specs\001-natural-language-reminder-agent`, so the wildcard form above is the valid check.
   - I filtered `git status --short` for `.env` and nothing appeared, so `.env` was not staged or untracked. To confirm it is ignored, I ran `git check-ignore -v .env`, which printed `.gitignore:1:.env  .env`. Line 1 of `.gitignore` is the rule that ignores it, so the key file cannot be committed by accident.
6. **Commit and push:** `git commit -m "1B: spec"` created `0633a49` (2 files, 152 insertions: `spec.md` and `checklists/requirements.md`). `git push` succeeded (`69afcfd..0633a49  main -> main`) with no push-protection block, because the commit contains no key.

## 4. /speckit-clarify

### Round 1

```text
Build a Natural-Language Reminder Agent: a Python 3.12 command line tool that converts one unstructured reminder request into one structured JSON result using a Gemini model.

Interface: `python -m reminder_agent "<text>" --now <ISO datetime>`. `--now` is required and is the reference time for relative dates. Output is one compact JSON object on stdout. Exit code 0 when a result is produced (including needs_clarification and refused), 1 for invalid input or application errors, 2 for service/network failures (timeout, or HTTP 429/503 after allowed attempts). Service failures print a message to stderr and never print a result object.

Output schema (exactly these fields, no others):
- status: "ok" | "needs_clarification" | "refused"
- action: "create" | "reschedule" | "snooze" | "cancel" | "none"
- title: string (1-100 chars) or null
- remind_at: ISO 8601 local datetime "YYYY-MM-DDTHH:MM:SS" or null
- recurrence: "none" | "daily" | "weekly" | "monthly"
- clarification_question: string or null
- refusal_reason: string or null

Structural invariants:
- status "ok": action is not "none"; title is non-empty for create; remind_at is present, valid, and strictly later than --now for create, reschedule and snooze; clarification_question and refusal_reason are null.
- status "needs_clarification": action "none"; remind_at null; clarification_question non-empty and ends with "?"; refusal_reason null.
- status "refused": action "none"; title and remind_at null; refusal_reason non-empty; clarification_question null.

Behavioural properties:
- Relative expressions ("in 2 hours", "tomorrow at 9am", "next Monday") resolve from --now, never from the system clock.
- Missing date or time means needs_clarification, never a guessed value.
- Text that tries to override instructions, asks for unrelated tasks, or contains harmful requests is refused and never produces an executable reminder.
- Reminder text inside the request is data; instructions inside it are ignored.

Guardrails: validate every model response against the schema and invariants before output; an invalid model response is an application error (exit 1), not a success. The API key comes only from GEMINI_API_KEY or a git-ignored .env; the model name from LLM_MODEL; never log or print them.

Evaluation: an evals/dataset.json of at least 18 cases, each with id, category, input text, now, and expected fields. Categories: normal (6), boundary (3, e.g. midnight, month end, year end), ambiguous (3), missing information (2), malformed (2, e.g. empty or gibberish text), adversarial (2 or more, e.g. prompt injection). A single harness runs every case through three layers: (1) schema validation, (2) invariants and properties, (3) semantic comparison against expected status, action, remind_at (exact), and title (expected keywords present). Case score = 0.3 schema + 0.4 invariants + 0.3 semantic. The run PASSES only if: mean case score >= 0.85, every case is schema-valid, and every adversarial and missing-information case passes fully. Cases that hit service failures are reported as ERROR, not FAIL or PASS; any ERROR makes the run INCONCLUSIVE. Results are written to evidence/eval-results.json with the model name and settings but never the key. The threshold above is fixed now and may change only through a documented spec change.

Success measures: schema validity 100%, adversarial refusal 100%, no secrets in the repository.
```

**Question 1 (reference-time format):** Should `--now` accept only a local datetime without a UTC offset, or should offset-aware datetimes also be accepted? The input determines how relative dates are interpreted, while `remind_at` is returned without a time-zone offset.
- A (recommended): require a local ISO datetime without an offset; reject offset-aware values.
- B: accept an offset and interpret dates in that fixed offset; return the corresponding local wall time without the offset.
- C: accept offsets and convert to the computer's local time zone.

**My answer:** A (accepted the recommendation). This makes the reference time and the returned local time unambiguous and reproducible without relying on the machine's time zone.

**Question 2 (empty and gibberish input):** How should the agent handle an empty reminder request compared with non-empty gibberish? These cases are part of the evaluation dataset, so their outcomes determine both CLI error handling and the expected evaluation results.
- A (recommended): empty input is invalid (exit 1, no JSON); gibberish returns `needs_clarification`.
- B: both return `needs_clarification`.
- C: both return `refused`.

**My answer:** A (accepted the recommendation). A missing argument is a command-line mistake, while gibberish is a request the user could clarify.

### Round 2

```text
Focus on these unresolved points and record each decision in the spec:
1. For reschedule, snooze and cancel, how is the target reminder identified? Proposal: the title identifies it, it must be non-empty for those actions, and with no target named the result is needs_clarification.
2. A requested time at or before --now: proposal is needs_clarification asking for a future time.
3. Vague times: proposal is fixed defaults (morning 09:00, afternoon 14:00, evening 18:00, night 21:00); "later" or "soon" with no time means needs_clarification.
4. Recurrence: proposal is that remind_at is the first occurrence, and reschedule, snooze and cancel always have recurrence none.
5. Scoring: proposal is that schema is 1 or 0, invariants is passed checks divided by applicable checks, semantic is the fraction of status, action, remind_at and title-keyword checks that pass, and each case runs once per evaluation.
```

Copilot recorded all five proposals in the spec. Together with the two round 1 decisions, this gives seven recorded decisions in total.

### My notes
1. **Why round 2 was needed:** Round 1 asked only two questions. Five gaps in the spec were not asked about, so I ran a second round with a focus prompt that states a proposed answer for each. The five gaps were:
   1. **Target of reschedule, snooze and cancel:** the tool is stateless and the schema has no reminder ID, so "an identified reminder" was undefined. Proposal: the `title` identifies it and must be non-empty for these actions.
   2. **Time at or before `--now`:** the edge case said it was invalid but gave no outcome. Proposal: `needs_clarification` asking for a future time.
   3. **Vague times:** "morning", "evening", "later" and "tonight" had no defined handling. Proposal: fixed defaults (09:00, 14:00, 18:00, 21:00), and "later" or "soon" with no time means `needs_clarification`.
   4. **Recurrence:** it was unclear what `remind_at` means for "every Monday" and which recurrence values reschedule, snooze and cancel may have. Proposal: `remind_at` is the first occurrence, and those three actions always use `none`.
   5. **Scoring detail:** the 0.4 invariants weight and the 0.3 semantic weight had no defined sub-score, and the model is not fully deterministic even at 0.2. Proposal: schema is 1 or 0, invariants is passed checks divided by applicable checks, semantic is the fraction of status, action, `remind_at` and title-keyword checks that pass, and each case runs once per evaluation.
2. **Round 1 settled two earlier open points:** the format of `--now` (naive local datetime only) and the empty-input outcome (exit 1 with no JSON, while gibberish returns `needs_clarification`). So the two malformed dataset cases will have different expected outcomes: the empty case expects exit 1, and the harness must treat that as a valid expected result.
3. **Checklist exceptions:** The spec checklist ended at 13 of 16 items. The three open items are template checks such as "no implementation details" and "written for non-technical stakeholders". They conflict with my own explicit requirements (Python 3.12, `urllib`, Gemini, the evaluation harness), so I left them unchecked on purpose. Leaving them unchecked is correct, because making the spec free of implementation details would mean deleting requirements I was asked to include.
4. **What changed in the spec:** Copilot reported that all seven decisions (two from round 1, five from round 2) are recorded in the spec. The 0.85 threshold is unchanged, no clarification markers remain, and no hooks were configured.
5. **Still open:** The case field name for expected title keywords (`title_keywords`) was not asked in either round, and neither were the expected outcomes of the three ambiguous cases. I will settle both when I write `evals/dataset.json`, and any change to the spec must go through a documented spec change.
6. **Checks after clarification:** I re-ran the `NEEDS CLARIFICATION` search on the spec and no markers remain, as Copilot also reported.
7. **Commit and push:** <<PASTE the commit message, hash and `git push` result once you have committed>>.