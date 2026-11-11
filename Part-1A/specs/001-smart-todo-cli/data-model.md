# Data Model: Smart Todo CLI

## Task

One task is a user's unit of work. Task objects use the following field order in CLI JSON output and persisted JSON:

| Field | Type | Constraints |
|---|---|---|
| `id` | positive integer | Unique; monotonically allocated from the stored `next_id`; never reused after deletion. |
| `title` | string | Trim surrounding whitespace; must remain non-empty. |
| `priority` | string enum | `low`, `medium`, or `high`; defaults to `medium` on add. |
| `tags` | array of strings | Zero or more trimmed, non-empty, case-sensitive values; duplicates within a task are invalid; defaults to `[]`. Preserve the supplied order. |
| `status` | string enum | `todo`, `doing`, or `done`; defaults to `todo` on add. |

The CLI must not expose an initial-status option. An edit preserves `id` and `status`, and changes only fields supplied. `--tag` on edit replaces the entire tag array; `--clear-tags` replaces it with an empty array. An edit with no edit options or with both `--tag` and `--clear-tags` is a validation error and leaves task data unchanged.

## Status transitions

| Current | Requested | Result |
|---|---|---|
| `todo` | `doing` | Allowed |
| `doing` | `done` | Allowed |
| `doing` | `todo` | Allowed |
| Any other pair, including same status | Any recognized status | Reject as an illegal transition; do not persist a change. |
| Any current status | Unrecognized value | Reject as validation error; do not persist a change. |

## Persisted document

The default path is `todo.json` in the current working directory. `--data-file PATH` overrides it; relative paths resolve from the current working directory. The JSON root is an object containing:

| Key | Type | Meaning |
|---|---|---|
| `version` | integer | Current document format version: `1`. Unsupported versions are rejected. |
| `next_id` | positive integer | ID to assign on the next successful add; remains above every previously allocated ID, including deleted IDs. |
| `tasks` | array of task objects | Current tasks; each object has exactly the fields and order defined above. |

Example (whitespace is insignificant to the stored format):

```json
{
  "version": 1,
  "next_id": 2,
  "tasks": [
    {
      "id": 1,
      "title": "Review proposal",
      "priority": "high",
      "tags": ["work"],
      "status": "todo"
    }
  ]
}
```

On load, validate the document structure, each task's fields and values, unique IDs, and `next_id` consistency before allowing a command to modify or list it. A missing file represents `next_id: 1` with no tasks. Malformed, unreadable, inconsistent, or unsupported-version data is an error; leave the file untouched.

## Mutation and ordering rules

- Validate the complete requested operation before writing; invalid edits are all-or-nothing.
- Persist successful mutations by serializing to a same-directory temporary file and atomically replacing the target.
- List membership is all tasks, or tasks containing any exact case-sensitive tag supplied as a filter.
- Sort lists by priority rank `high`, `medium`, `low`, then ascending numeric ID.
