# Research: Smart Todo CLI

All technology and interface choices needed for design were supplied by the user or resolved by the feature specification. No open technical unknowns remain.

## Runtime and command parsing

- **Decision**: Implement for Python 3.12 using only the standard library at runtime; use `argparse` for command/option parsing.
- **Rationale**: This is an explicit requirement, avoids runtime dependency installation, and supports a conventional `python -m todo` entry point.
- **Alternatives considered**: Third-party CLI frameworks such as Click or Typer were rejected because they add runtime dependencies and contradict the standard-library-only constraint.

## Task storage

- **Decision**: Persist a versioned JSON document with an integer `next_id` and a `tasks` array, using `json` for serialization.
- **Rationale**: JSON is required; the version allows strict format validation, and the persisted counter prevents ID reuse when the highest-numbered task has been deleted.
- **Alternatives considered**: A bare task array cannot retain the next ID after deletion. SQLite and external storage services conflict with the specified local JSON format.

## Persistence safety

- **Decision**: Fully load and validate before mutation; write a temporary file in the target directory and replace the target atomically only after the operation is valid.
- **Rationale**: Failed validation and unreadable/malformed input must not alter persisted data; same-directory replacement avoids exposing a partially serialized target file.
- **Alternatives considered**: Directly truncating and rewriting the target could leave corrupt/partial data on a failed write and was rejected.

## CLI and observable behavior

- **Decision**: Implement the supplied command grammar exactly, with one optional list `--tag`, repeatable add/edit `--tag`, edit tag replacement, and `--clear-tags`; reject edits with no edit option or with both tag-setting options. Emit one compact JSON value plus one newline for each successful command.
- **Rationale**: This resolves the spec's planning choice about command spelling and filename and preserves its exact stdout contract.
- **Alternatives considered**: Human-readable or pretty-printed output was rejected because it violates the defined compact JSON contract.

## Testing and quality tools

- **Decision**: Use pytest black-box subprocess tests with `PYTHONPATH=src` and `tmp_path`; run ruff and Bandit as development checks.
- **Rationale**: This is explicitly requested and validates invocation boundaries, persistence between processes, output bytes, errors, and exit codes.
- **Alternatives considered**: Unit-only tests were rejected because they cannot prove the public CLI contract or cross-invocation persistence.

## Performance reference

- **Decision**: Test both full and tag-filtered listing with 10,000 pre-created tasks; take five full-process timings per case, including stdout capture, and assert each median is at most two seconds on Python 3.12.
- **Rationale**: This is the measurement method in the spec and ensures the output itself is included in the timing.
- **Alternatives considered**: Timing only the service function or using a single run was rejected because it omits process/serialization costs or is too noisy.
- **Environment observed**: Windows 11 Pro 10.0.22621; Intel Core i7-8550U @ 1.80 GHz; 7.9 GB visible memory; project virtual environment Python 3.12.16.
