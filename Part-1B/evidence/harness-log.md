# Harness Log – Part 1B

## 1. Setup
- **Model and settings used (no key):** the conclusive run used `gemini-3.5-flash-lite`, chosen through `LLM_MODEL` in my git-ignored `.env`. Model calls use temperature 0.2, a 30-second timeout and at most three attempts, retrying only HTTP 429 and 503. The pass threshold is a mean case score of 0.85.
- **What the harness checks, in my words:** it runs every case in `evals/dataset.json` exactly once through the real command-line entry point (`cli.main` with arguments), and records the output, the error text and the exit code. Each case gets three scores. Schema is 1 or 0: did the output match the result schema, or, for the empty-input case, the "exit 1, no JSON, safe error message" contract. Invariants is the share of applicable rule checks that passed. Semantic is the share of four checks that passed: status, action, exact reminder time and title keywords. The case score is 0.3 × schema + 0.4 × invariants + 0.3 × semantic.
- **Pass rule:** the run passes only if the mean score is at least 0.85, every result-producing case is schema-valid, the empty-input case meets its contract, and every adversarial and missing-information case scores fully. If any case hits a service failure it is marked `ERROR`, and the whole run is `INCONCLUSIVE`, never a pass or a fail.

## 2. Initial generation
- I did the work in stages instead of running all tasks at once. Stage A wrote the tests and the dataset before any implementation (`fe30860`, 20:27). Stage B wrote the implementation (`f35b8fe`, 20:46), and I tagged that commit `1B-initial-generation`.
- The tag points at the first generated implementation as it was, before I changed anything. That version still contains the failing test described in the next section, so the baseline is honest.

## 2a. Fix made after the tag
- Two minutes after tagging, I made one manual change (`6796252`, 20:48). Copilot's report after the implementation stage said 67 passed and 3 failed. The failures were in the Phase 2 CLI tests, which read `CaptureResult.stdout` where pytest's capture object calls it `.out`. I had told Copilot not to edit the Phase 2 tests, so it left them, and I made the one-line change myself. When I ran the tests myself I saw the same pytest error that Copilot had reported: `CaptureResult` has no `stdout`.
- `git show --stat` confirms the commit changed one line in `tests/test_cli.py` (1 insertion, 1 deletion) and nothing else. So I did not touch the dataset, the expected values, the threshold or the evaluators.

## 3. Quality gates (before repair)
Saved in `evidence/quality-gates-initial.txt` (committed in `9e3e17f`, 21:00) before any repair.
- **ruff:** 19 errors, 5 of them fixable automatically. Most were E501 (lines longer than 88 characters), plus E402 (imports not at the top of `.harness/run_eval.py`), F401 (unused import), UP035 and UP041 (outdated import and exception style) and one I001 (import order).
- **bandit:** 1 Medium issue, B310 (the `urlopen` call may accept non-HTTPS schemes), at `src/reminder_agent/client.py:132`. It scanned 385 lines of code. The constitution requires zero medium or high findings, so this failed the gate.
- **pytest:** 70 passed. So the behaviour was fine, and the failures were about code quality and security style.

## 4. Repairs
The constitution allows at most two automated repair attempts per set of failures. There were two sets of failures (this one, and the configuration defect in section 5), and I used both attempts on each. For this first set, the quality-gate failures:
- **Repair attempt 1** (`562208f`, 21:13, "ruff and bandit, partial"): I asked Copilot to fix the ruff and bandit findings. The Copilot terminal crashed with memory errors during this attempt, so I could not rely on its report and checked the results myself. What was left afterwards were the ruff errors that can be fixed automatically, which is why I committed it as "partial".
- **Repair attempt 2** (`a24c149`, 21:15): `ruff check --fix`, which applies the automatic fixes. It cleaned up the ruff errors that attempt 1 left behind.
- **After the repairs (final gates):** I re-ran all three gates on the finished code and saved the output in `evidence/quality-gates-final.txt`. The bandit report is stamped 17:04 UTC, which is about 22:35 local time, after the last commit.
  - **ruff:** "All checks passed!" (19 errors before).
  - **bandit:** "No issues identified", with 0 Low, 0 Medium and 0 High findings (1 Medium before). It scanned 405 lines of code (385 before). It also shows 0 lines skipped by `#nosec` and 0 issues disabled, so the B310 finding was fixed in the code and not hidden with a suppression, which the constitution forbids.
  - **pytest:** 71 passed (70 before). The one extra test is probably from the tests added in the `.env` fix (section 5).
- **Did I accept the result, and why:** yes. After the two attempts, ruff and bandit are clean and every test still passes, so the quality gates in the constitution are met. The repairs stayed inside the limit of two attempts per set.
- **Check on the harness file:** several of the long lines were in `.harness/run_eval.py`, which holds the evaluator rules, and the constitution forbids editing the evaluators. I compared the file before the repairs (`9e3e17f`) with the file after repair 2 (`a24c149`). The changes are:
  - the unused `datetime` import was removed;
  - the imports that ruff flagged (E402) were moved from the top of the file into a small function, `_load_runtime()`, which loads the CLI and validation modules the first time they are needed;
  - the code now refers to those modules as `validation.ACTIONS` and so on;
  - long lines were wrapped.
  I saved the full diff to `$env:TEMP\harness-diff-1.txt` (a temporary folder, so it is not committed) and read all of it. I also searched the diff for the score weight and threshold lines, and the search printed nothing, so no weight or threshold line was changed. In the diff I read, the edits to the checks are only wrapping and the new module references.
- **Disclosure:** this was a refactor of the evaluator file, made only to satisfy ruff, and it was made before the first evaluation produced any result. I am recording it here so it is visible. The scoring rules, weights and threshold were not changed.

## 5. Harness defect
- **What went wrong:** when I first ran the harness against the live model it stopped with "LLM_MODEL must be configured". That message came from the harness itself, not from Gemini, so the problem was how the harness read its configuration, not the model or the quota. The harness stopped at start-up, so no evaluation result existed before this fix.
- **How it was fixed:** `0e63c89` (21:32), "fix harness .env configuration loading". It changed `.harness/run_eval.py` (23 lines) and `tests/test_harness.py` (45 lines): 61 insertions and 7 deletions in total. No file under `src/` changed, so the agent itself was not touched. I treated this as a defect in the harness setup, not as a change to the scoring.
- **Two attempts on this set of failures:** the constitution allows 2 repair attempts per set of failures, and this configuration defect was a new set with its own count. I used both attempts on it. Attempt 1 was the Copilot prompt that made the harness read its settings through the same `.env` code as the application. After that attempt, Copilot reported one import-order error left in `tests/test_harness.py` that was already there before its change. Attempt 2 was `ruff check --fix`, which fixed that import-order error. I did not make a separate commit for it: both attempts went into the same commit, `0e63c89`. So this set is also at its limit of two attempts, and no repair attempt remained for it.
- **Why this matters:** both changed files are on the evaluation side, so I am recording the change openly. I read the diff of `.harness/run_eval.py` between `a24c149` and `0e63c89`. The visible change only alters how the model name is loaded (`load_settings()` and `ConfigurationError`), and no scoring line, weight or threshold appears in it. Copilot's report says it did not read `.env` during this fix. That statement comes from its report, not from something I could observe myself.

## 6. Evaluation runs
Each run's result is kept as its own file in `evidence/`.

| Run | Model | Outcome | Counts | Why |
|---|---|---|---|---|
| 1 | `gemini-3.8-flash` | INCONCLUSIVE | 1 PASS, 18 ERROR | HTTP 429 rate limits on the model calls. |
| 2 | `gemini-3.8-flash` | INCONCLUSIVE | 1 PASS, 18 ERROR | Same model and the same 429 rate limits, so this was a straight re-run. |
| 3 | `gemini-3.5-flash` | INCONCLUSIVE | 11 PASS, 8 ERROR | I changed the model; fewer 429s, but still 8 cases failed with service errors. |
| 4 | `gemini-3.5-flash-lite` | PASS | 19 PASS | I changed the model again; no service errors. Mean case score 1.0. |

- **What I changed between runs:** only the model name in `.env`. I did not change the code, the dataset, the threshold or the evaluators.
- **Why the errors count as service failures:** after three attempts on a 429, the client raises a service error, the command exits with code 2, and the harness marks that case `ERROR`. That is the behaviour the constitution requires.
- **A warning about runs 1 to 3:** the files show `mean=1.0` for these runs. That number is only the mean of the cases that actually ran (the one case or the 11 cases that did not hit an error). It says nothing about the cases that errored. These runs are `INCONCLUSIVE` because any `ERROR` makes the whole run inconclusive, whatever the mean says, so nobody should read them as passes. The 1 PASS in runs 1 and 2 was `malformed-01-empty`, which I confirmed from the result files. It is the empty-input case, which makes no model call and so cannot be rate limited.

## 7. Decision
- **ACCEPT** run 4 (`3220cec`, 22:03, "first conclusive evaluation PASS 19/19") as the evaluation result.
- **Reasoning:** it is the first run with no service errors, so it is the first conclusive one. All 19 cases passed, including the empty-input contract and every adversarial and missing-information case, and the mean score is 1.0, above the fixed 0.85 threshold. The dataset, expected values, threshold and scoring rules were not changed between the runs, so the earlier inconclusive runs and the final pass are comparable. The quality gates are also clean (section 4). I also checked that the API key is not in the repository: I searched the working tree and all of the git history for the actual key value from my `.env`, and found no key value.
- **Limit of this result:** the pass was reached on `gemini-3.5-flash-lite`, a different model from runs 1 and 2. A 1.0 mean on 19 cases shows the agent meets the specification on this dataset, not that it is perfect on all inputs. The residual risks are listed in section 7a.
- **Tags:** `1B-initial-generation` (the first generated implementation) and `1B-final` both exist in the repository. At the end, `1B-final` and `HEAD` are the same commit, the working tree is clean and up to date with `origin/main`, and `.env` is ignored and not tracked.

## 7a. Evidence added after the evaluation (12 Nov)

I added this on 12 November, after the accepted run. None of it changes the evaluation itself. The dataset, the expected values, the threshold and the evaluators were not touched.

- **Layer results for run 4 (19 cases):** the schema average was 1.0, the invariants average was 1.0 and the semantic average was 1.0. So the mean case score was 1.0, against the fixed threshold of 0.85.
- **No evaluation FAIL, and no evaluation-driven repair:** no run produced a `FAIL`. Runs 1 to 3 were `INCONCLUSIVE` because of rate limits, and run 4 was a `PASS`. So I did not need any harness-driven repair of the application. The two repair sets in this log were for other reasons: the quality gates (ruff and bandit) and the harness configuration defect.
- **Snapshots of the code at the two tags:** `evidence/initial-generation/` holds `src`, `.harness` and `evals` as they were at the tag `1B-initial-generation`. `evidence/final-generation/` holds the same three folders at the tag `1B-final`. I extracted both from git without editing them, and I added them on 12 November, after the evaluation. I did not copy `tests`, because it already exists in git at each tag, and a second copy inside `evidence/` would also be collected by pytest. Comparing the two snapshots shows everything that changed after the first generation, including the lint refactor of `.harness/run_eval.py` and the configuration fix described in sections 4 and 5.
- **Traceability:** `evidence/traceability.md` maps each evaluation case to the requirement in the specification that it checks. I wrote it after the dataset was locked, so it describes the dataset and did not shape it, and I did not change the dataset while writing it. AI helped me draft the file, and I reviewed it myself against the specification.
- **Residual risks:**
  - There are only 19 cases, and each case ran once, so a 1.0 score is a small sample.
  - The only conclusive pass is on one model, `gemini-3.5-flash-lite`. The other models I tried were rate limited, so I have no result for them.
  - The title and clarification checks are keyword and rule based. They catch missing keywords and wrong formats, but they do not check whether a title or a question really means the right thing.
  - The model is not deterministic even at temperature 0.2, so a later run could score differently, and I have not measured how much.

## 8. What I would do differently
- Run `ruff` and `bandit` as soon as the implementation is generated, and before tagging, so the gates do not fail on routine style problems and cost two repair attempts.
- Write the harness to the lint rules from the start (imports at the top, lines under 88 characters), so that a lint repair never has to edit the evaluator file.
- Test that the harness reads `.env` before the first live run. A small test would have caught the "LLM_MODEL must be configured" defect without a live call.
- Check model availability and rate limits with a single case before a full 19-case run. Runs 1 to 3 were spent on rate limits, not on testing the agent.
- Report the number of cases that actually ran next to the mean, so an inconclusive run can never look like a pass in the evidence files.
- Run the evaluation more than once on the passing model, to see how much the results vary, which I did not do here.