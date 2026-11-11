"""Black-box acceptance tests for the Smart Todo CLI.

Covers AC-01 to AC-19, AC-21 and AC-22 from specs/001-smart-todo-cli/spec.md.
AC-20 (performance) is in test_cli_performance.py.
Every test name and docstring carries its AC id for traceability.
"""

import json

import pytest

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def task(task_id, title, priority="medium", tags=(), status="todo"):
    """Build a task dict with keys in the contract order."""
    return {
        "id": task_id,
        "title": title,
        "priority": priority,
        "tags": list(tags),
        "status": status,
    }


def compact(value):
    """Exact expected stdout: one compact JSON value plus one newline."""
    return json.dumps(value, separators=(",", ":")) + "\n"


def ordered(tasks):
    """Expected list order: priority high, medium, low, then numeric ID ascending."""
    return sorted(tasks, key=lambda t: (PRIORITY_RANK[t["priority"]], t["id"]))


def state(path):
    """Snapshot of a data path: bytes, 'directory', or None when absent."""
    if path.is_dir():
        return "directory"
    return path.read_bytes() if path.exists() else None


def assert_failure(result, before, path):
    """Common failure contract: exit 1, empty stdout, stderr diagnostic, no mutation."""
    assert result.code == 1
    assert result.out == ""
    assert result.err.strip() != ""
    assert state(path) == before


# ---------------------------------------------------------------- AC-01, AC-02


def test_ac01_add_uses_defaults_and_persists(cli, data_file):
    """AC-01: add with only a title uses medium priority, no tags, status todo."""
    result = cli("add", "Write report")
    expected = task(1, "Write report")
    assert result.code == 0
    assert result.out == compact(expected)
    assert result.err == ""
    assert data_file.exists()
    listed = cli("list")
    assert listed.code == 0
    assert listed.out == compact([expected])


def test_ac02_add_stores_supplied_fields(cli):
    """AC-02: supplied priority and tags are stored; status is todo."""
    result = cli("add", "Plan trip", "--priority", "high", "--tag", "work", "--tag", "urgent")
    expected = task(1, "Plan trip", "high", ["work", "urgent"])
    assert result.code == 0
    assert result.out == compact(expected)
    assert result.err == ""
    assert cli("list").out == compact([expected])


# ----------------------------------------------------------------------- AC-03

INVALID_ADD = [
    pytest.param(["add"], id="missing-title"),
    pytest.param(["add", ""], id="empty-title"),
    pytest.param(["add", "   "], id="blank-title"),
    pytest.param(["add", "Task", "--priority", "urgent"], id="unsupported-priority"),
    pytest.param(["add", "Task", "--tag", ""], id="empty-tag"),
    pytest.param(["add", "Task", "--tag", "   "], id="blank-tag"),
    pytest.param(["add", "Task", "--tag", "a", "--tag", "a"], id="duplicate-tag"),
    pytest.param(["add", "Task", "--tag", "a", "--tag", " a "], id="duplicate-tag-after-trim"),
]

INVALID_EDIT_AND_IDS = [
    pytest.param(["edit", "1", "--title", ""], id="edit-empty-title"),
    pytest.param(["edit", "1", "--title", "   "], id="edit-blank-title"),
    pytest.param(["edit", "1", "--priority", "urgent"], id="edit-unsupported-priority"),
    pytest.param(["edit", "1", "--tag", ""], id="edit-empty-tag"),
    pytest.param(["edit", "1", "--tag", "a", "--tag", "a"], id="edit-duplicate-tag"),
    pytest.param(["edit", "abc", "--title", "X"], id="edit-non-integer-id"),
    pytest.param(["edit", "0", "--title", "X"], id="edit-zero-id"),
    pytest.param(["edit", "1.5", "--title", "X"], id="edit-decimal-id"),
    pytest.param(["status", "abc", "doing"], id="status-non-integer-id"),
    pytest.param(["delete", "0"], id="delete-zero-id"),
    pytest.param(["delete", "abc"], id="delete-non-integer-id"),
]


@pytest.mark.parametrize("args", INVALID_ADD + INVALID_EDIT_AND_IDS)
def test_ac03_rejects_invalid_title_priority_and_tags_atomically(
    args, cli, data_file, make_store
):
    """AC-03: invalid add/edit input and malformed IDs exit 1 and change nothing."""
    make_store([task(1, "Existing", "low", ["keep"])])
    before = state(data_file)
    assert_failure(cli(*args), before, data_file)


@pytest.mark.parametrize("args", INVALID_ADD)
def test_ac03_invalid_add_on_missing_file_creates_nothing(args, cli, data_file):
    """AC-03: a rejected add must not create the data file."""
    assert_failure(cli(*args), None, data_file)


# ---------------------------------------------------------------- AC-04, AC-05


def test_ac04_list_orders_by_priority_then_numeric_id(cli, make_store):
    """AC-04: priority high/medium/low, then ID ascending; numeric, not textual."""
    tasks = [
        task(12, "t12", "low"),
        task(3, "t3", "high"),
        task(10, "t10", "medium"),
        task(1, "t1", "low"),
        task(11, "t11", "high"),
        task(2, "t2", "medium"),
        task(9, "t9", "medium"),
        task(4, "t4", "high"),
        task(5, "t5", "low"),
        task(8, "t8", "medium"),
        task(6, "t6", "high"),
        task(7, "t7", "low"),
    ]
    make_store(tasks)
    result = cli("list")
    assert result.code == 0
    assert result.err == ""
    assert result.out == compact(ordered(tasks))
    assert [t["id"] for t in json.loads(result.out)] == [3, 4, 6, 11, 2, 8, 9, 10, 1, 5, 7, 12]


def test_ac05_tag_filter_is_exact_and_keeps_order(cli, make_store):
    """AC-05: exact, case-sensitive, whole-tag match; same ordering as AC-04."""
    tasks = [
        task(1, "Low work", "low", ["work"]),
        task(2, "Capital Work", "high", ["Work"]),
        task(3, "High work", "high", ["work", "home"]),
        task(4, "Homework", "medium", ["homework"]),
        task(5, "Untagged", "medium"),
        task(6, "Medium work", "medium", ["work"]),
    ]
    make_store(tasks)
    work = cli("list", "--tag", "work")
    assert work.code == 0
    assert work.err == ""
    assert work.out == compact([tasks[2], tasks[5], tasks[0]])
    assert cli("list", "--tag", "Work").out == compact([tasks[1]])
    assert cli("list", "--tag", "homework").out == compact([tasks[3]])


# ----------------------------------------------------------------------- AC-06


def test_ac06_empty_and_unmatched_lists_succeed(cli, make_store, data_file):
    """AC-06: no tasks, or no tag match, is success with an empty array."""
    missing = cli("list")
    assert (missing.code, missing.out, missing.err) == (0, "[]\n", "")
    assert not data_file.exists()
    filtered_missing = cli("list", "--tag", "nothing")
    assert (filtered_missing.code, filtered_missing.out) == (0, "[]\n")

    make_store([task(1, "Only", "high", ["a"])])
    unmatched = cli("list", "--tag", "zzz")
    assert (unmatched.code, unmatched.out, unmatched.err) == (0, "[]\n", "")


# ---------------------------------------------------------------- AC-07, AC-08

EDIT_CASES = [
    pytest.param(
        ["--title", "New title"],
        task(1, "New title", "high", ["a"], "doing"),
        id="title-only",
    ),
    pytest.param(
        ["--priority", "low"],
        task(1, "Old title", "low", ["a"], "doing"),
        id="priority-only",
    ),
    pytest.param(
        ["--tag", "x", "--tag", "y"],
        task(1, "Old title", "high", ["x", "y"], "doing"),
        id="tags-replace-whole-set",
    ),
    pytest.param(
        ["--clear-tags"],
        task(1, "Old title", "high", [], "doing"),
        id="clear-tags",
    ),
    pytest.param(
        ["--title", "T", "--priority", "medium", "--tag", "z"],
        task(1, "T", "medium", ["z"], "doing"),
        id="all-fields",
    ),
]


@pytest.mark.parametrize(("edit_args", "expected"), EDIT_CASES)
def test_ac07_edit_changes_only_requested_fields(edit_args, expected, cli, make_store):
    """AC-07: only requested fields change; ID, status and other tasks are intact."""
    other = task(2, "Other", "low")
    make_store([task(1, "Old title", "high", ["a"], "doing"), other])
    result = cli("edit", "1", *edit_args)
    assert result.code == 0
    assert result.out == compact(expected)
    assert result.err == ""
    assert cli("list").out == compact(ordered([expected, other]))


INVALID_EDIT_MIXED = [
    pytest.param(["--title", "  ", "--priority", "low"], id="blank-title-with-valid-priority"),
    pytest.param(["--priority", "urgent", "--title", "New"], id="bad-priority-with-valid-title"),
    pytest.param(["--tag", "a", "--tag", "a", "--title", "New"], id="duplicate-tag-with-title"),
    pytest.param(["--tag", "", "--title", "New"], id="empty-tag-with-title"),
]


@pytest.mark.parametrize("edit_args", INVALID_EDIT_MIXED)
def test_ac08_invalid_edit_is_atomic(edit_args, cli, data_file, make_store):
    """AC-08: one invalid value rejects the whole edit; valid parts are not applied."""
    make_store([task(1, "Old title", "high", ["a"], "doing")])
    before = state(data_file)
    assert_failure(cli("edit", "1", *edit_args), before, data_file)


# ---------------------------------------------------------------- AC-09 .. AC-12


def _assert_allowed_transition(cli, make_store, current, new):
    other = task(2, "Other")
    make_store([task(1, "Ship it", "high", ["rel"], current), other])
    result = cli("status", "1", new)
    expected = task(1, "Ship it", "high", ["rel"], new)
    assert result.code == 0
    assert result.out == compact(expected)
    assert result.err == ""
    assert cli("list").out == compact(ordered([expected, other]))


def test_ac09_todo_to_doing(cli, make_store):
    """AC-09: todo -> doing is allowed and persisted."""
    _assert_allowed_transition(cli, make_store, "todo", "doing")


def test_ac10_doing_to_done(cli, make_store):
    """AC-10: doing -> done is allowed and persisted."""
    _assert_allowed_transition(cli, make_store, "doing", "done")


def test_ac11_doing_to_todo(cli, make_store):
    """AC-11: doing -> todo is allowed and persisted."""
    _assert_allowed_transition(cli, make_store, "doing", "todo")


DISALLOWED = [
    ("todo", "todo"),
    ("todo", "done"),
    ("doing", "doing"),
    ("done", "todo"),
    ("done", "doing"),
    ("done", "done"),
]


@pytest.mark.parametrize(("current", "new"), DISALLOWED)
def test_ac12_rejects_all_disallowed_and_same_status_transitions(
    current, new, cli, data_file, make_store
):
    """AC-12: every recognized but disallowed transition is an illegal transition."""
    make_store([task(1, "Ship it", "high", ["rel"], current)])
    before = state(data_file)
    result = cli("status", "1", new)
    assert_failure(result, before, data_file)
    assert "illegal transition" in result.err.lower()


# ----------------------------------------------------------------------- AC-13


def test_ac13_delete_removes_task_from_output_and_file(cli, data_file, make_store):
    """AC-13: deleted task disappears from listings and the file; IDs are not reused."""
    make_store([task(1, "Remove me"), task(2, "Keep me", "high")])
    result = cli("delete", "1")
    assert result.code == 0
    assert result.out == compact({"deleted": 1})
    assert result.err == ""
    assert cli("list").out == compact([task(2, "Keep me", "high")])
    assert "Remove me" not in data_file.read_text(encoding="utf-8")

    # Assumption in the spec: IDs are never reused after deletion.
    assert cli("delete", "2").code == 0
    again = cli("add", "Fresh")
    assert again.out == compact(task(3, "Fresh"))


# ----------------------------------------------------------------------- AC-14

MISSING_ID_COMMANDS = [
    pytest.param(["edit", "99", "--title", "X"], id="edit"),
    pytest.param(["status", "99", "doing"], id="status"),
    pytest.param(["delete", "99"], id="delete"),
]


@pytest.mark.parametrize("args", MISSING_ID_COMMANDS)
def test_ac14_edit_delete_and_status_report_missing_id(args, cli, data_file, make_store):
    """AC-14: a positive ID that does not exist is task-not-found, exit 1."""
    make_store([task(1, "Existing")])
    before = state(data_file)
    result = cli(*args)
    assert_failure(result, before, data_file)
    assert "not found" in result.err.lower()


@pytest.mark.parametrize("args", MISSING_ID_COMMANDS)
def test_ac14_missing_id_with_no_data_file_creates_nothing(args, cli, data_file):
    """AC-14: not-found on a missing data file reports an error and creates no file."""
    result = cli(*args)
    assert_failure(result, None, data_file)
    assert "not found" in result.err.lower()


# ----------------------------------------------------------------------- AC-15


def test_ac15_changes_survive_separate_cli_invocations(cli):
    """AC-15: each command is its own process; saved state is visible to the next."""
    assert cli("add", "First", "--priority", "low", "--tag", "a").code == 0
    assert cli("add", "Second", "--priority", "high").code == 0
    assert cli("status", "1", "doing").code == 0
    assert cli("edit", "2", "--tag", "b").code == 0
    expected = [
        task(2, "Second", "high", ["b"], "todo"),
        task(1, "First", "low", ["a"], "doing"),
    ]
    listed = cli("list")
    assert listed.code == 0
    assert listed.out == compact(expected)


# ----------------------------------------------------------------------- AC-16


def _assert_contract(result):
    """One compact JSON value, exactly one trailing newline, nothing on stderr."""
    assert result.code == 0
    assert result.err == ""
    assert result.out.endswith("\n")
    assert result.out.count("\n") == 1
    value = json.loads(result.out)
    assert result.out == compact(value)
    return value


def _assert_task_keys(value):
    assert list(value.keys()) == ["id", "title", "priority", "tags", "status"]


def test_ac16_success_stdout_matches_compact_json_contract(cli):
    """AC-16: exact stdout shape for add, edit, status, list and delete."""
    added = _assert_contract(cli("add", "Plan: step one, step two", "--tag", "a"))
    _assert_task_keys(added)

    edited = _assert_contract(cli("edit", "1", "--priority", "high"))
    _assert_task_keys(edited)

    changed = _assert_contract(cli("status", "1", "doing"))
    _assert_task_keys(changed)

    listed = _assert_contract(cli("list"))
    assert isinstance(listed, list)
    assert len(listed) == 1
    _assert_task_keys(listed[0])

    empty = cli("list", "--tag", "nothing")
    assert _assert_contract(empty) == []
    assert empty.out == "[]\n"

    deleted = _assert_contract(cli("delete", "1"))
    assert list(deleted.keys()) == ["deleted"]
    assert deleted == {"deleted": 1}


# ----------------------------------------------------------------------- AC-17

VALID_TASK = task(1, "a", "low")
BAD_STORES = [
    pytest.param("{not json", id="malformed-json"),
    pytest.param("[]", id="wrong-shape"),
    pytest.param(
        json.dumps({"version": 2, "next_id": 2, "tasks": [VALID_TASK]}),
        id="unsupported-version",
    ),
    pytest.param(
        json.dumps({"version": 1, "next_id": 1, "tasks": [VALID_TASK]}),
        id="next-id-not-above-existing-id",
    ),
    pytest.param(
        json.dumps({"version": 1, "next_id": 3, "tasks": [VALID_TASK, VALID_TASK]}),
        id="duplicate-ids",
    ),
    pytest.param(
        json.dumps(
            {"version": 1, "next_id": 2, "tasks": [task(1, "a", "urgent")]}
        ),
        id="invalid-persisted-task",
    ),
]
DATA_COMMANDS = [
    pytest.param(["list"], id="list"),
    pytest.param(["add", "New task"], id="add"),
    pytest.param(["edit", "1", "--title", "X"], id="edit"),
    pytest.param(["status", "1", "doing"], id="status"),
    pytest.param(["delete", "1"], id="delete"),
]


@pytest.mark.parametrize("args", DATA_COMMANDS)
@pytest.mark.parametrize("content", BAD_STORES)
def test_ac17_malformed_or_unreadable_data_file_is_unchanged(
    content, args, cli, data_file
):
    """AC-17: a bad existing data file is reported, exit 1, and never rewritten."""
    data_file.write_text(content, encoding="utf-8")
    before = state(data_file)
    assert_failure(cli(*args), before, data_file)


@pytest.mark.parametrize("args", DATA_COMMANDS)
def test_ac17_unreadable_path_is_reported_and_left_alone(args, cli, data_file):
    """AC-17: a directory at the data path cannot be read; portable on Windows."""
    data_file.mkdir()
    assert_failure(cli(*args), "directory", data_file)
    assert list(data_file.iterdir()) == []


# ----------------------------------------------------------------------- AC-18


@pytest.mark.parametrize("value", ["blocked", "finished", "in-progress", ""])
def test_ac18_unknown_status_is_validation_error(value, cli, data_file, make_store):
    """AC-18: an unrecognized status is a validation error, not an illegal transition."""
    make_store([task(1, "Ship it", "high", [], "doing")])
    before = state(data_file)
    result = cli("status", "1", value)
    assert_failure(result, before, data_file)
    assert "illegal transition" not in result.err.lower()


# ----------------------------------------------------------------------- AC-19


def test_ac19_explicitly_empty_tag_filter_is_rejected(cli, data_file, make_store):
    """AC-19: `list --tag ""` is a validation error."""
    make_store([task(1, "Existing", "low", ["a"])])
    before = state(data_file)
    assert_failure(cli("list", "--tag", ""), before, data_file)


# ----------------------------------------------------------------------- AC-21


def test_ac21_data_file_override_supports_absolute_and_relative_paths(run_todo, tmp_path):
    """AC-21: --data-file is honoured (absolute and relative); default is cwd/todo.json."""
    absolute = tmp_path / "custom.json"
    result = run_todo("--data-file", str(absolute), "add", "Absolute")
    assert result.code == 0
    assert absolute.exists()
    assert not (tmp_path / "todo.json").exists()

    relative_cwd = tmp_path / "relative_cwd"
    relative_cwd.mkdir()
    result = run_todo("--data-file", "rel.json", "add", "Relative", cwd=relative_cwd)
    assert result.code == 0
    assert (relative_cwd / "rel.json").exists()
    assert not (relative_cwd / "todo.json").exists()

    default_cwd = tmp_path / "default_cwd"
    default_cwd.mkdir()
    result = run_todo("add", "Default", cwd=default_cwd)
    assert result.code == 0
    assert (default_cwd / "todo.json").exists()
    listed = run_todo("list", cwd=default_cwd)
    assert listed.out == compact([task(1, "Default")])


# ----------------------------------------------------------------------- AC-22

INVALID_EDIT_FORMS = [
    pytest.param(["edit", "1"], id="no-edit-options"),
    pytest.param(["edit", "1", "--tag", "a", "--clear-tags"], id="tag-and-clear-tags"),
    pytest.param(
        ["edit", "1", "--title", "New", "--clear-tags", "--tag", "x"],
        id="title-with-conflicting-tag-options",
    ),
]


@pytest.mark.parametrize("args", INVALID_EDIT_FORMS)
def test_ac22_edit_without_changes_or_conflicting_tag_flags_rejected(
    args, cli, data_file, make_store
):
    """AC-22: edit with no options, or with --tag plus --clear-tags, is rejected."""
    make_store([task(1, "Existing", "low", ["keep"])])
    before = state(data_file)
    assert_failure(cli(*args), before, data_file)
