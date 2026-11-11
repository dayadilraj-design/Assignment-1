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
   - **What happened:** `git push` was rejected with `error: failed to push some refs`. GitHub secret scanning reported "Push cannot contain secrets" and flagged a *GCP API Key Bound to a Service Account* in commit `87398da5017cc1518db0216ba33d62f58deaf01f`, at `Part-1B/.env.example:1`. The `.env.example` in that earlier commit had a real-looking key on the first line instead of a placeholder.
   - **Why it matters:** The key lived in a local commit's history. Changing the file afterwards would not have helped, because GitHub scans every commit being pushed, not just the latest version of the file.
   - **Fix (history rewrite, not an "allow secret" bypass):**
     1. Checked that the current file only has the placeholder: `Select-String -Path .env.example -Pattern "replace_with_your_key" -Quiet` returned `True`.
     2. `git reset --soft origin/main` undid my local commits but kept all the changes staged, so the commit with the key was no longer part of what I push.
     3. `git add .` re-staged everything with the corrected `.env.example`.
     4. Verified what would be committed with `git show ":./.env.example"`. It showed only `GEMINI_API_KEY=replace_with_your_key` and `LLM_MODEL=replace_with_available_model_name`. `git status --short` showed the three expected files (`.env.example`, `.specify/memory/constitution.md`, `evidence/prompts-used.md`).
     5. `git commit -m "1B: constitution"` created one clean commit (`b139f74`).
     6. `git push` succeeded: `4eb9fae..b139f74  main -> main`.
   - **Follow-up:** I did not use GitHub's "allow this secret" URL. Because the push was blocked, the key never reached GitHub. Since it was a real-looking key, I will revoke or rotate it in Google Cloud and keep only placeholders in `.env.example`. The real key stays in `.env`, which is git-ignored.