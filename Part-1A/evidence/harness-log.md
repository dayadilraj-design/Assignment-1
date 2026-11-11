# Harness log: Part 1A (Smart Todo CLI)

## 1. Initial generation and context

I used GitHub Spec Kit with Copilot in Agent mode (VS Code). The order was constitution, specify, clarify, plan, tasks, analyze, implement. The exact prompts are in `evidence/prompts-used.md`.

By the time I ran implement, the spec had 22 acceptance criteria (AC-01 to AC-22) and tasks.md had T001 to T012. AC-22 was not in the first spec. I added it after reading plan.md (prompt 4b), because the plan had quietly made "edit with no options" a valid no-op and I wanted that to be an error.

The implement prompt limited Copilot to `src/todo/`. It was told not to touch `tests/`, `.harness/`, spec.md, plan.md or the constitution, and not to use `# noqa` or `# nosec`. It was also told not to run the tests or the harness, so the first real result would come from my own run.

The first generated code is kept in `evidence/initial-generation/` and tagged `1A-initial-generation` (commit 4d08f4c). The tests and harness baseline is tag `1A-harness-baseline` (commit 8cb75c9). The generated code is six files (`__init__`, `__main__`, `cli`, `models`, `service`, `storage`), 426 lines in total.

## 2. Harness setup

The harness is `.harness/run_harness.py`. It runs three gates one after another and does not stop at the first failure:

| Gate | Command | Passes when |
|---|---|---|
| lint | `python -m ruff check src tests` | exit 0, no errors |
| security | `python -m bandit -r src -ll -q` | exit 0, no medium or high findings |
| tests | `python -m pytest tests -q` | exit 0, nothing failing |

Tool versions: Python 3.12.16, ruff 0.17.4, bandit 1.9.4, pytest 9.2.0.

The overall result is PASS only if all three pass. Each run writes a `.json` and a `.txt` file to `evidence/harness-results/`, named by timestamp.

The tests are in `tests/test_cli.py`, with helpers in `conftest.py`. They call `python -m todo` as a subprocess with a temporary `--data-file`, so they only check the CLI's visible behaviour. Every AC from 01 to 22 is mentioned in at least one test. AC-20 (10,000 tasks within 2 seconds) is in `test_cli_performance.py`, which also saves its timings to `harness-results/performance.json`.

Claude (the chat assistant) drafted the harness script, `pytest.ini` and the tests, working from spec.md and the plan's AC-to-test table. My part was reviewing them against the spec, deciding what to keep, and committing and tagging them as `1A-harness-baseline` before implement. The tag gives me something to diff against afterwards to show Copilot did not change them.

## 3. Harness executions

Environment: Windows 11, Python 3.12.16, 7.9 GB RAM, Intel64 Family 6 Model 142 CPU.

| Run | Time | Lint | Security | Tests | Overall |
|---|---|---|---|---|---|
| 1 | 2026-11-11 14:38:54 | PASS (0.39 s) | PASS (1.53 s) | PASS, 104 passed (35.39 s as timed by the harness; pytest itself reported 33.19 s) | PASS |

Files: `evidence/harness-results/run-20261111-143854.json` and `.txt`.

Performance result for AC-20, 10,000 tasks, 5 runs each:
- unfiltered list: median 0.283 s
- tag-filtered list: median 0.256 s
- the limit is 2.0 s, so both are well under it

Integrity check (`evidence/integrity-check.txt`): `git diff` against `1A-harness-baseline` for `tests` and `.harness` was empty, so Copilot did not change either of them.

This was the only harness run. There was no second run because the first one passed.

## 4. Failures and repairs

There were none. All three gates passed on the first run, so I used 0 of the 2 allowed repair attempts. I compared `src/todo/` with `evidence/initial-generation/src/todo/` and there is no difference, so `src/` is still the first generated code.

## 5. My review

What I checked after the run:

- Tests and harness are unchanged since the baseline tag (integrity check above).
- I searched `src/` for `noqa`, `nosec`, `eval(`, `exec(`, `pickle` and `shell=True` and found none.
- The runtime imports are standard library only (argparse, json, os, tempfile, pathlib, dataclasses, typing), which is what the constitution requires.
- All 22 AC IDs appear in the test files.
- The performance medians are far below the 2 second limit, so NFR-003 does not look like a risk on this machine.

What I saw in `src/todo/`: the structure matches plan.md (`cli.py`, `service.py`, `models.py`, `storage.py`, plus `__main__.py`). `storage.py` saves by writing to a temporary file in the same directory (`tempfile.NamedTemporaryFile`) and then `os.replace`, so a failed write should not leave a half-written data file. I also ran four commands by hand with `PYTHONPATH=src` set. My very first attempt failed with "No module named todo" because I had not set it. I then ran them twice, once to see the output and once with `$LASTEXITCODE` after each. The second pass used the same `scratch.json`, which already held tasks 1 and 2, so the new IDs there were 3 and 4. I deleted `scratch.json` afterwards.

| Command | Exit code | What it shows |
|---|---|---|
| `add "Hello"` | 0 | task printed as compact JSON (id 1 on the first pass, 3 on the second), priority medium, no tags, status todo |
| `add "-weird title"` | 0 | accepted, title kept as `-weird title` (id 2, then 4) |
| `--data-file nofolder\x.json add "A"` | 1 | `error: could not write task data file ...: [Errno 2] No such file or directory`. The write failure is reported, not a crash. The message includes the temporary file name, which is a bit noisy. |
| `list --tag` (no value) | 1 | `error: argument --tag: expected one argument`. The argparse error exits with 1 instead of its default 2, which is what the spec's exit-code rule needs. |

Things I noticed:
- 104 tests passed but there are only 25 test functions. 11 of them use `parametrize` (12 decorators in total, because the AC-17 malformed-file test has two). So 104 is the number of cases, not the number of functions.
- A green run only shows that the tests I wrote pass. If I missed a case in the spec when writing the tests, this harness would not catch it.

## 6. Final decision

Accept. Lint, security and all 104 tests passed on the first run, the tests and harness were not modified, and the performance requirement is met with a lot of room. No repair was needed.

Limits:
- This is a single run on one Windows machine, and the result is only as good as my tests.
- The tests use ASCII titles only, so behaviour with non-ASCII titles is not tested.
- The tests check for the words "illegal transition" and "not found" in error messages. I set those words in the implement prompt; the spec itself does not require them.