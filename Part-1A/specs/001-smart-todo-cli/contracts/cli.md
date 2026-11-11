# CLI Contract

## Invocation

Run from the project root with `PYTHONPATH=src`:

```text
python -m todo [--data-file PATH] add TITLE [--priority low|medium|high] [--tag TAG ...]
python -m todo [--data-file PATH] list [--tag TAG ...]
python -m todo [--data-file PATH] edit ID [--title TITLE] [--priority P] [--tag TAG ...] [--clear-tags]
python -m todo [--data-file PATH] status ID STATUS
python -m todo [--data-file PATH] delete ID
```

The default data path is `todo.json` in the current working directory. Relative `--data-file` values resolve against that directory. `--tag` is repeatable. On `list`, repeated tags select tasks matching any supplied tag, with each comparison being exact and case-sensitive. On `edit`, one or more `--tag` values replace the complete tag set; `--clear-tags` empties it. Supplying both edit options is invalid. With no edit options, `edit ID` is a no-op and returns the task. The option `--tag ""` is an explicitly empty filter and is invalid.

## Standard output

Every successful command prints exactly one compact JSON value followed by exactly one newline. No status text or other success output is written.

| Command | JSON value |
|---|---|
| `add` | Complete created task object. |
| `list` | Array of complete task objects, including `[]` for no results. |
| `edit` | Complete updated task object (or unchanged object for a no-op edit). |
| `status` | Complete updated task object. |
| `delete` | `{"deleted":<id>}` with the deleted numeric ID. |

Task object keys are ordered `id`, `title`, `priority`, `tags`, `status`; list ordering is priority `high`, `medium`, `low`, then numeric ID ascending. JSON is compact (no insignificant spaces).

Example:

```text
{"id":1,"title":"Review proposal","priority":"medium","tags":[],"status":"todo"}
```

## Standard error and exit codes

| Outcome | stderr | Exit code | Data mutation |
|---|---|---:|---|
| Successful command | Empty | 0 | Per command; list does not mutate. |
| Invalid arguments/value (including unknown status or empty tag filter) | Diagnostic error | 1 | None. |
| Recognized but disallowed status transition (including same status) | Illegal-transition diagnostic | 1 | None. |
| ID does not exist for edit/status/delete | Task-not-found diagnostic | 1 | None. |
| Existing file is malformed, unreadable, inconsistent, or has unsupported format | Data-file diagnostic | 1 | None; do not rewrite the file. |
| Help request | Help text on stdout | 0 | None. |

Error wording is not fixed by the spec; diagnostics must identify the category and go to stderr. Argument-parser validation errors use exit code 1 rather than argparse's default usage-error code 2.

Non-integer or non-positive IDs are validation errors. A positive integer ID that is not present in the loaded collection is a task-not-found error.

## Persisted JSON envelope

The file is a versioned object with `version`, `next_id`, and `tasks`. `tasks` contains task objects in the same field order as output. The schema, ID allocation rules, and validation rules are detailed in [data-model.md](../data-model.md).
