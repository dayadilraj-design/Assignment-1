# Feature Specification: Smart Todo CLI

**Feature Branch**: `main`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "Build a Smart Todo CLI for a single user. Features: add, list, edit and delete tasks. Each task has an id, title, priority (low, medium, high), tags, and status (todo, doing, done). Allowed status transitions only: todo->doing, doing->done, doing->todo. Any other transition must be rejected. Filter the task list by tag. List sorted by priority (high first) with a deterministic tie-break. Persist all tasks in a local JSON file. Exit codes: 0 on success; 1 on validation error, illegal transition, or task not found. Write user stories, functional and non-functional requirements, and numbered binary acceptance criteria (AC-01, AC-02, ...) in Given/When/Then form with exact expected outcomes and exit codes. List assumptions and open questions. Do not describe the implementation."

## Clarifications

### Session 2026-11-11

- Q: What exact stdout format should successful add, list, edit, status, and delete commands use? → A: Compact JSON: add, edit, and status print the complete task object; list prints an array; delete prints `{"deleted":<id>}`. Task keys are ordered `id`, `title`, `priority`, `tags`, `status`; each command prints one JSON value followed by a newline.
- Q: What should the CLI do when the task data file exists but is malformed or cannot be read? → A: Report the problem on stderr, exit `1`, and leave the file untouched.
- Q: How should a user change a task's status, and how should an unrecognized status value be handled? → A: Use a dedicated `status` command; an unrecognized value is a validation error, while a known but disallowed transition is an illegal transition. Both report on stderr, exit `1`, and leave task data unchanged.
- Q: How should the 10,000-task, two-second list performance requirement be measured, and which environment should serve as the reference? → A: Use the developer's machine with Python 3.12 and record its OS, CPU, and memory; time the full CLI process through complete stdout capture for unfiltered and tag-filtered lists over pre-created 10,000-task data, using the median of five runs for each.
- Q: How should tests and users select a temporary task data file instead of the default file? → A: Use `--data-file <path>`; resolve relative paths from the current working directory.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage Tasks (Priority: P1)

As the single user, I want to add, view, edit, and remove tasks so that I can keep an accurate list of work.

**Why this priority**: Task management is the core value of the CLI.

**Independent Test**: Add a task, list it, edit its details, delete it, and verify each resulting task state independently.

**Acceptance Scenarios**:

1. **Given** a valid task title and optional priority and tags, **When** the user adds a task, **Then** the CLI creates a uniquely identified task with status `todo` and reports success with exit code `0`.
2. **Given** an existing task, **When** the user edits its title, priority, or tags with valid values, **Then** only the requested fields change, the task keeps its ID and status, and the CLI exits `0`.
3. **Given** an existing task, **When** the user deletes it, **Then** it is absent from subsequent lists and the CLI exits `0`.

---

### User Story 2 - Track Task Progress (Priority: P1)

As the single user, I want to move tasks through the allowed workflow so that task progress is accurate and invalid jumps are prevented.

**Why this priority**: Status is a required task attribute, and enforcing the specified workflow prevents invalid progress states.

**Independent Test**: Exercise every allowed status transition and verify that each other requested transition is rejected without changing the task.

**Acceptance Scenarios**:

1. **Given** a task with status `todo`, **When** the user changes its status to `doing`, **Then** the task is updated and the CLI exits `0`.
2. **Given** a task with status `doing`, **When** the user changes its status to `done` or `todo`, **Then** the task is updated and the CLI exits `0`.
3. **Given** a task, **When** the user requests any status transition not listed above, including retaining the current status, **Then** the request is rejected, the task remains unchanged, and the CLI exits `1`.

---

### User Story 3 - Find and Prioritize Tasks (Priority: P2)

As the single user, I want to filter tasks by tag and see tasks in a predictable priority order so that I can focus on relevant work.

**Why this priority**: Filtering and ordering make the task list useful as it grows.

**Independent Test**: List all tasks and a tag-filtered subset, checking exact membership and ordering for each result.

**Acceptance Scenarios**:

1. **Given** tasks with different priorities, **When** the user lists tasks, **Then** tasks appear in `high`, `medium`, `low` order, with equal-priority tasks ordered by ascending ID, and the CLI exits `0`.
2. **Given** tasks with and without a requested tag, **When** the user lists tasks filtered by that tag, **Then** only tasks with an exact matching tag appear in the same priority order, and the CLI exits `0`.

### Edge Cases

- Listing when there are no tasks, or when a valid tag filter matches none, returns an empty result and exit code `0`.
- A missing local task file is treated as an empty task collection; the first successful addition creates persisted task data.
- An invalid title, priority, tag, or task identifier is a validation error: no task data changes and the CLI exits `1`.
- An edit that contains multiple changes is all-or-nothing; if any requested value is invalid, none of its changes are applied.
- Editing, deleting, or changing the status of an ID that does not exist reports task-not-found and exits `1`.
- An existing malformed or unreadable task data file is reported on stderr with exit code `1`; the file is left untouched.
- Tasks tied on priority remain in ascending ID order on every list, including filtered lists.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST allow the single user to add, list, edit, and delete tasks.
- **FR-002**: Each task MUST have a unique ID, a non-empty title, a priority of `low`, `medium`, or `high`, zero or more tags, and a status of `todo`, `doing`, or `done`.
- **FR-003**: The CLI MUST assign each new task a unique ID and initialize its status to `todo`.
- **FR-004**: The CLI MUST allow a user to edit a task's title, priority, and tags without changing its ID or status.
- **FR-005**: The CLI MUST allow only the status transitions `todo` to `doing`, `doing` to `done`, and `doing` to `todo`. It MUST reject every other requested transition, including a request to set the current status again.
- **FR-006**: The CLI MUST reject invalid task values, illegal transitions, and references to nonexistent task IDs with exit code `1`; successful operations MUST exit with code `0`.
- **FR-007**: The CLI MUST list all tasks or filter them by an exact tag match. A tag-filtered list MUST contain only tasks with that tag.
- **FR-008**: Every task list MUST sort by priority in descending order (`high`, `medium`, `low`) and then by ID in ascending order. This order MUST be deterministic.
- **FR-009**: The CLI MUST persist all task fields in a local JSON file and retain successful changes across separate invocations.
- **FR-010**: Failed validation and illegal-transition operations MUST leave task data unchanged. A missing task data file MUST behave as an empty collection.
- **FR-011**: A list with no matching tasks MUST be a successful operation with exit code `0`.
- **FR-012**: Successful add, edit, and status commands MUST print the complete task as one compact JSON object followed by a newline; list MUST print the task array in compact JSON, including `[]` for no results; delete MUST print `{"deleted":<id>}` as compact JSON followed by a newline. Task object keys MUST appear in the order `id`, `title`, `priority`, `tags`, `status`.
- **FR-013**: If the existing task data file is malformed or cannot be read, the CLI MUST report an error on stderr, exit `1`, and leave the file unchanged.
- **FR-014**: The CLI MUST provide a dedicated `status` command to change a task's status. An unrecognized status value MUST be reported as a validation error; a recognized but disallowed transition MUST be reported as an illegal transition. Either error MUST be reported on stderr, exit `1`, and leave task data unchanged.
- **FR-015**: An explicitly empty tag filter MUST be rejected as a validation error, reported on stderr, with exit code `1` and no task data changes.
- **FR-016**: The CLI MUST accept `--data-file <path>` to select the task data file instead of the default; relative paths MUST resolve from the current working directory.

### Non-Functional Requirements

- **NFR-001**: Given the same persisted tasks and list request, the CLI MUST produce the same task membership and ordering.
- **NFR-002**: Task data MUST remain local to the single user's environment and be available after the CLI exits.
- **NFR-003**: On the developer's machine running Python 3.12, whose OS, CPU, and memory are recorded with the result, unfiltered and tag-filtered lists over a pre-created collection of 10,000 tasks MUST each complete and display all results within 2 seconds at the median of five runs. Timing MUST start at CLI process launch and end when all stdout has been captured.
- **NFR-004**: Success and failure MUST be distinguishable by the specified exit code; validation, transition, and not-found failures MUST provide an error indication without modifying task data.

### Acceptance Criteria

- **AC-01** — **Given** no task data exists, **When** the user adds a task with a non-empty title and no optional values, **Then** exactly one task is created with a unique ID, priority `medium`, no tags, and status `todo`; the created task and its ID are reported, persisted, and the exit code is `0`.
- **AC-02** — **Given** the user supplies a valid title, priority, and tags, **When** the user adds the task, **Then** those supplied values are stored on the new task, status is `todo`, and the exit code is `0`.
- **AC-03** — **Given** an add or edit request has a missing or blank title, unsupported priority, or blank/duplicate tag, **When** the CLI validates the request, **Then** it reports a validation error, changes no task data, and exits `1`.
- **AC-04** — **Given** multiple tasks with mixed priorities and IDs, **When** the user lists all tasks, **Then** every task appears exactly once, ordered by priority `high` then `medium` then `low`, with IDs ascending within each priority, and the exit code is `0`.
- **AC-05** — **Given** tasks where some have the exact requested tag, **When** the user lists tasks filtered by that tag, **Then** the result contains exactly those matching tasks in the AC-04 ordering, and the exit code is `0`.
- **AC-06** — **Given** no tasks exist or no task has the requested tag, **When** the user lists all tasks or applies the tag filter, **Then** the result contains zero tasks and the exit code is `0`.
- **AC-07** — **Given** an existing task, **When** the user edits its title, priority, and/or tags using valid values, **Then** the requested fields change, all unrequested fields and the ID remain unchanged, the updated task is persisted, and the exit code is `0`.
- **AC-08** — **Given** an existing task and an edit request with any invalid value, **When** the CLI processes the edit, **Then** the edit is rejected atomically, the task remains exactly as it was, and the exit code is `1`.
- **AC-09** — **Given** a task with status `todo`, **When** the user runs the dedicated `status` command to set status `doing`, **Then** the task status becomes `doing`, the change is persisted, and the exit code is `0`.
- **AC-10** — **Given** a task with status `doing`, **When** the user runs the dedicated `status` command to set status `done`, **Then** the task status becomes `done`, the change is persisted, and the exit code is `0`.
- **AC-11** — **Given** a task with status `doing`, **When** the user runs the dedicated `status` command to set status `todo`, **Then** the task status becomes `todo`, the change is persisted, and the exit code is `0`.
- **AC-12** — **Given** a task in any status, **When** the user runs the dedicated `status` command to request a recognized status other than `todo` to `doing`, `doing` to `done`, or `doing` to `todo` (including the current status), **Then** the CLI reports an illegal transition on stderr, leaves the task unchanged, and exits `1`.
- **AC-13** — **Given** an existing task, **When** the user deletes it, **Then** it is absent from subsequent listings and persisted task data, and the exit code is `0`.
- **AC-14** — **Given** an ID that does not identify a task, **When** the user attempts to edit, delete, or change that task's status, **Then** the CLI reports task-not-found, changes no task data, and exits `1`.
- **AC-15** — **Given** a successful change has been made, **When** the user starts a separate CLI invocation and lists tasks, **Then** the previously saved task fields and state are present, and the exit code is `0`.
- **AC-16** — **Given** a successful add, edit, status, list, or delete command, **When** the command writes to stdout, **Then** add, edit, and status print exactly one compact JSON task object; list prints exactly one compact JSON task array (or `[]` when empty); delete prints exactly one compact JSON object with the `deleted` key and the deleted ID as its value. Task object keys appear in the order `id`, `title`, `priority`, `tags`, `status`, and each JSON value is followed by exactly one newline.
- **AC-17** — **Given** an existing task data file that is malformed or unreadable, **When** the user runs a command that accesses task data, **Then** the CLI prints an error to stderr, exits `1`, and leaves the file unchanged.
- **AC-18** — **Given** an existing task, **When** the user runs the dedicated `status` command with a value other than `todo`, `doing`, or `done`, **Then** the CLI reports a validation error on stderr, leaves the task unchanged, and exits `1`.
- **AC-19** — **Given** any task collection, **When** the user lists tasks with an explicitly empty tag filter, **Then** the CLI reports a validation error on stderr, changes no task data, and exits `1`.
- **AC-20** — **Given** a pre-created file containing 10,000 valid tasks and the developer's Python 3.12 machine with its OS, CPU, and memory recorded, **When** the CLI performs an unfiltered list and a tag-filtered list, each measured five times from process launch through complete stdout capture, **Then** the median duration for each operation is at most 2 seconds.
- **AC-21** — **Given** a path to a temporary task data file, **When** the user invokes the CLI with `--data-file <path>`, **Then** the CLI reads and writes task data at that path instead of the default file; a relative path is resolved from the current working directory.

### Key Entities

- **Task**: A user's unit of work, identified by a unique ID and containing a title, priority, zero or more tags, and workflow status.
- **Tag**: A user-supplied label associated with a task and used for exact-match filtering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 21 acceptance criteria pass with their specified task data outcomes, output, and exit codes.
- **SC-002**: Users can complete an add, list, edit, and delete cycle with each successful command returning exit code `0`.
- **SC-003**: For a pre-created collection of 10,000 tasks, unfiltered and tag-filtered lists each have a median wall-clock duration of at most 2 seconds across five runs on the developer's Python 3.12 machine; record the machine's OS, CPU, and memory.
- **SC-004**: Across repeated list requests over unchanged data, 100% of task lists have identical membership and ordering.

## Assumptions

- The feature is for one user and does not include accounts, collaboration, or synchronization between devices.
- A newly added task defaults to priority `medium`, no tags, and status `todo`; the user cannot choose an initial status other than `todo`.
- IDs are generated as positive integers, increase as tasks are created, and are not reused after deletion; ascending numeric ID is the tie-break for equal priority.
- Titles and tag values are trimmed and must be non-empty. Tags are free-form, case-sensitive strings; duplicate tags on one task are invalid.
- Tag filtering uses an exact, case-sensitive match. A missing tag filter means list all tasks; an explicitly empty filter is a validation error.
- The default local JSON task file is associated with the CLI's current working directory. Its exact filename and the main CLI command spelling are decisions for planning. `--data-file <path>` overrides the default file; relative override paths are resolved from the current working directory.
- Validation errors, illegal transitions, and task-not-found errors are indicated on the error output stream; exact message wording is not prescribed.
- Malformed or unreadable task data is reported on stderr with exit code `1`, without changing the file.

## Open Questions

- None block specification readiness. The exact data filename and command syntax remain planning decisions; error wording is not prescribed.
