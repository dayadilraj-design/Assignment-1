---

description: "Implementation tasks for the Smart Todo CLI source package"
---

# Tasks: Smart Todo CLI

**Input**: Design documents from `specs/001-smart-todo-cli/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/cli.md, research.md

**Scope**: Implement `src/todo/` only. Do not create or modify tasks for `tests/` or `.harness/`; acceptance tests and harness are prepared by the human.

## Phase 1: Setup

**Purpose**: Create the Python package and its module entry point.

- [ ] T001 [P] Create the `src/todo/` package initializer in `src/todo/__init__.py`, keeping runtime imports standard-library-only (FR-001, NFR-002).
- [ ] T002 [P] Create `src/todo/__main__.py` to invoke `todo.cli.main()` and return its process exit code so `python -m todo` is the public entry point (FR-001, AC-16, NFR-004).

## Phase 2: Foundational

**Purpose**: Implement the validated task representation, persistent JSON format, and shared CLI parsing behavior required by all stories.

- [ ] T003 Define `Task` validation and ordered JSON conversion in `src/todo/models.py` using the data-model constraints verbatim: `id` is a positive integer; **Unique; monotonically allocated from the stored `next_id`; never reused after deletion.** `title`: **Trim surrounding whitespace; must remain non-empty.** `priority`: **`low`, `medium`, or `high`; defaults to `medium` on add.** `tags`: **Zero or more trimmed, non-empty, case-sensitive values; duplicates within a task are invalid; defaults to `[]`. Preserve the supplied order.** `status`: **`todo`, `doing`, or `done`; defaults to `todo` on add.** Serialize task fields in the exact order `id`, `title`, `priority`, `tags`, `status`; do not provide an initial-status option (FR-002, FR-003, FR-012, AC-01, AC-02, AC-03, AC-16).
- [ ] T004 Implement `load_tasks` and atomic `save_tasks` in `src/todo/storage.py` for the version-1 JSON envelope `{version, next_id, tasks}`. Require `version` integer `1`; require positive-integer `next_id` (the ID to assign on the next successful add) to remain above every previously allocated ID, including deleted IDs. Treat a missing file as `next_id: 1` with no tasks; reject malformed, unreadable, unsupported-version, structurally invalid, duplicate-ID, or inconsistent-`next_id` data without rewriting it. Validate each persisted task before returning it. Serialize to a same-directory temporary file and atomically replace the target only after a valid mutation (FR-003, FR-009, FR-010, FR-013, AC-01, AC-15, AC-17).
- [ ] T005 Build the shared `argparse` parser and CLI bootstrap in `src/todo/cli.py` for `add`, `list`, `edit`, `status`, and `delete`, with global `--data-file PATH` before the command. Resolve relative data paths from the current working directory and default to `todo.json` there. Normalize parser/value errors to exit code 1 while preserving help on stdout with exit code 0; provide shared dispatch and diagnostic/JSON-output helpers for the story handlers (FR-001, FR-006, FR-012, FR-016, AC-16, AC-21, NFR-004).

## Phase 3: User Story 1 - Manage Tasks (Priority: P1)

**Goal**: Add, list, edit, and delete tasks while preserving all task fields not selected for editing.

**Independent Test Criteria**: Invoke add, list, edit, and delete against a temporary `--data-file`; verify each success response and the resulting persisted task state, including that edits preserve ID and status and deletion removes the task.

### Implementation

- [ ] T006 [US1] Implement add, basic all-task listing, edit, and delete operations in `src/todo/service.py`. Allocate IDs using stored `next_id`; initialize new tasks to `todo`; preserve ID and status on edit; change only supplied fields; make edits all-or-nothing; reject edits with no edit options or simultaneous `--tag` and `--clear-tags`; report missing IDs without saving (FR-001, FR-002, FR-003, FR-004, FR-006, FR-009, FR-010, FR-017, AC-01, AC-02, AC-03, AC-07, AC-08, AC-13, AC-14, AC-15, AC-22).
- [ ] T007 [US1] Implement the `add`, `edit`, `delete`, and basic unfiltered `list` handlers in `src/todo/cli.py`; define their exact arguments (`add TITLE`, repeatable add/edit `--tag`, edit `--clear-tags`) and dispatch through `src/todo/service.py`. Return the complete task object for add/edit and `{"deleted":id}` for delete; emit one compact JSON value and one newline per successful command (FR-001, FR-004, FR-012, FR-017, AC-01, AC-02, AC-07, AC-13, AC-16, AC-22).

## Phase 4: User Story 2 - Track Task Progress (Priority: P1)

**Goal**: Permit only the specified status transitions and distinguish invalid status values from disallowed transitions.

**Independent Test Criteria**: With a valid stored task in each starting status, invoke the status command for all allowed transitions and confirm the updated task is persisted; request every disallowed and same-status transition and an unknown status, confirming exit code 1 and unchanged task data.

### Implementation

- [ ] T008 [US2] Implement the status operation and its error distinction in `src/todo/service.py`: allow only `todo`→`doing`, `doing`→`done`, and `doing`→`todo`; reject unknown statuses as validation errors and recognized but disallowed or same-status requests as illegal transitions; do not persist failures and report missing IDs as task-not-found (FR-005, FR-006, FR-010, FR-014, AC-09, AC-10, AC-11, AC-12, AC-14, AC-18, NFR-004).
- [ ] T009 [US2] Implement the `status ID STATUS` handler in `src/todo/cli.py`, dispatching through `src/todo/service.py`; print the complete updated task on success and map validation, illegal-transition, and not-found failures to stderr with exit code 1 (FR-005, FR-006, FR-012, FR-014, AC-09, AC-10, AC-11, AC-12, AC-14, AC-16, AC-18, NFR-004).

## Phase 5: User Story 3 - Find and Prioritize Tasks (Priority: P2)

**Goal**: Filter by exact tags and return every list in stable priority/ID order.

**Independent Test Criteria**: List a populated collection without a filter and with an exact tag filter; verify exact membership, ordering by `high`, `medium`, `low` and ascending numeric ID within each priority, empty results for no matches, and rejection of an explicitly empty filter.

### Implementation

- [ ] T010 [US3] Extend the list operation in `src/todo/service.py` to include all tasks or only tasks containing the exact requested tag, then sort by priority `high`, `medium`, `low` and ascending numeric ID. Keep filtering and sorting efficient enough to meet the 10,000-task list target of a median at most 2 seconds across five full CLI runs (FR-007, FR-008, FR-011, AC-04, AC-05, AC-06, AC-20, NFR-001, NFR-003).
- [ ] T011 [US3] Complete the `list [--tag TAG]` handler in `src/todo/cli.py`: accept at most one optional filter, reject an explicitly empty filter as a validation error, call the sorted/filtering service operation, and emit the complete compact JSON array (including `[]`) followed by one newline (FR-007, FR-008, FR-011, FR-012, FR-015, AC-04, AC-05, AC-06, AC-16, AC-19, NFR-001).

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ensure consistent error categories, exit codes, and output across the complete CLI.

- [ ] T012 Finalize shared error handling in `src/todo/cli.py` so data-file failures are diagnosed on stderr without mutation; invalid arguments/values, illegal transitions, and task-not-found each exit 1; success writes no stderr and exactly one compact JSON value plus one newline; and help writes to stdout and exits 0 (FR-006, FR-010, FR-012, FR-013, FR-014, AC-03, AC-08, AC-12, AC-14, AC-16, AC-17, AC-18, AC-19, AC-22, NFR-004).

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No prerequisites; T001 and T002 can be implemented in parallel.
- **Foundational (Phase 2)**: Depends on Setup. Complete T003 before T004; complete the shared parser/bootstrap T005 before story-specific CLI handlers. This phase blocks the stories.
- **User Story 1 (Phase 3)**: Depends on the foundation; complete T006 before T007.
- **User Story 2 (Phase 4)**: Depends on the foundation and follows User Story 1 because both stories extend `service.py` and `cli.py`; complete T008 before T009.
- **User Story 3 (Phase 5)**: Depends on the foundation and follows the earlier stories to avoid conflicting edits to `service.py` and `cli.py`; complete T010 before T011.
- **Polish (Phase 6)**: Depends on all story handlers.

### User Story Dependency Graph

```text
Setup -> Foundational -> US1 -> US2 -> US3 -> Polish
```

The story order is an implementation sequence for the shared source modules, not an additional runtime dependency between task workflows.

### Parallel Opportunities

- T001 and T002 edit separate package files and can proceed in parallel.
- Within each story, the service and CLI tasks are ordered because the CLI handler depends on the service operation and both stories touch shared modules.
- No implementation tasks target `tests/` or `.harness/`; the human-authored acceptance coverage is the independent validation source.

## Parallel Execution Examples

```text
# Setup: independent package files
T001: Create src/todo/__init__.py
T002: Create src/todo/__main__.py

# Stories: preserve service-before-handler order in the shared modules
US1: T006 -> T007
US2: T008 -> T009
US3: T010 -> T011
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete User Story 1 and validate add/list/edit/delete against the independent criteria.
3. This delivers the MVP task-management workflow; stop for human acceptance validation before proceeding.

### Incremental Delivery

1. Add User Story 2 and validate allowed/rejected progress transitions.
2. Add User Story 3 and validate exact-tag membership, stable ordering, and the 10,000-task performance target.
3. Complete cross-cutting CLI error/output handling, preserving the human-authored tests and harness unchanged.
