import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from todo.models import PRIORITIES, TodoError
from todo.service import add_task, delete_task, edit_task, list_tasks, set_status


class _ArgumentError(Exception):
    """Raised for command-line syntax errors that should exit with code 1."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentError(message)


def _positive_id(value: str) -> int:
    try:
        task_id = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ID must be a positive integer") from exc
    if task_id <= 0:
        raise argparse.ArgumentTypeError("ID must be a positive integer")
    return task_id


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="todo", allow_abbrev=False)
    parser.add_argument("--data-file", default="todo.json", metavar="PATH")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_ArgumentParser)

    add_parser = commands.add_parser("add", allow_abbrev=False)
    add_parser.add_argument("title")
    add_parser.add_argument("--priority", choices=PRIORITIES, default="medium")
    add_parser.add_argument("--tag", action="append", default=[])

    list_parser = commands.add_parser("list", allow_abbrev=False)
    list_parser.add_argument("--tag")

    edit_parser = commands.add_parser("edit", allow_abbrev=False)
    edit_parser.add_argument("id", type=_positive_id)
    edit_parser.add_argument("--title")
    edit_parser.add_argument("--priority", choices=PRIORITIES)
    edit_parser.add_argument("--tag", action="append")
    edit_parser.add_argument("--clear-tags", action="store_true")

    status_parser = commands.add_parser("status", allow_abbrev=False)
    status_parser.add_argument("id", type=_positive_id)
    status_parser.add_argument("status")

    delete_parser = commands.add_parser("delete", allow_abbrev=False)
    delete_parser.add_argument("id", type=_positive_id)
    return parser


def _emit_json(value: object) -> None:
    print(json.dumps(value, separators=(",", ":")))


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        arguments = parser.parse_args(argv)
        data_path = _resolve_path(arguments.data_file)

        if arguments.command == "add":
            task = add_task(
                data_path,
                arguments.title,
                priority=arguments.priority,
                tags=arguments.tag,
            )
            _emit_json(task.to_dict())
        elif arguments.command == "list":
            _emit_json([task.to_dict() for task in list_tasks(data_path, arguments.tag)])
        elif arguments.command == "edit":
            task = edit_task(
                data_path,
                arguments.id,
                title=arguments.title,
                priority=arguments.priority,
                tags=arguments.tag,
                clear_tags=arguments.clear_tags,
            )
            _emit_json(task.to_dict())
        elif arguments.command == "status":
            task = set_status(data_path, arguments.id, arguments.status)
            _emit_json(task.to_dict())
        else:
            deleted_id = delete_task(data_path, arguments.id)
            _emit_json({"deleted": deleted_id})
        return 0
    except (_ArgumentError, TodoError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
