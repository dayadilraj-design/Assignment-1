import argparse
import json
import sys
from collections.abc import Sequence
from urllib.error import HTTPError

from .client import ServiceError
from .core import Transport, run
from .validation import ValidationError, parse_local_datetime


class _InputError(Exception):
    pass


class _ParserExit(Exception):
    def __init__(self, status: int) -> None:
        self.status = status


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _InputError(message)

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            self._print_message(message, sys.stdout if status == 0 else sys.stderr)
        raise _ParserExit(status)


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="reminder_agent", allow_abbrev=False)
    parser.add_argument("text", help="one unstructured reminder request")
    parser.add_argument(
        "--now",
        required=True,
        metavar="YYYY-MM-DDTHH:MM:SS",
        help="required naive local reference datetime",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    transport: Transport | None = None,
) -> int:
    parser = _build_parser()
    try:
        arguments = parser.parse_args(argv)
        if not arguments.text.strip():
            raise _InputError("reminder text must not be empty")
        now = parse_local_datetime(arguments.now, field_name="--now")
        if now.tzinfo is not None:
            raise _InputError("--now must be a local datetime without an offset")
        result = run(arguments.text, now, transport)
        print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))
        return 0
    except _ParserExit as exc:
        return exc.status
    except _InputError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 1
    except ServiceError:
        print("Service error: the model service request failed.", file=sys.stderr)
        return 2
    except (ValidationError, ValueError, HTTPError):
        print("Application error: invalid input or model response.", file=sys.stderr)
        return 1
