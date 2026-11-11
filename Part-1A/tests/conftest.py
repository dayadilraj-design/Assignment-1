"""Shared fixtures for the black-box CLI acceptance tests.

The tests only use the public command line (`python -m todo`) and the persisted
JSON envelope documented in specs/001-smart-todo-cli/contracts/cli.md.
Nothing here imports the implementation.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


@dataclass(frozen=True)
class Result:
    """Outcome of one CLI invocation."""

    code: int
    out: str
    err: str


def run_process(args, cwd):
    """Run `python -m todo <args>` in a fresh process and capture everything."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else str(SRC) + os.pathsep + existing
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-m", "todo", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    return Result(proc.returncode, proc.stdout, proc.stderr)


@pytest.fixture
def run_todo(tmp_path):
    """Run the CLI with arbitrary arguments (including --data-file) and cwd."""

    def run(*args, cwd=None):
        return run_process(list(args), cwd or tmp_path)

    return run


@pytest.fixture
def data_file(tmp_path):
    """Path of the temporary task data file used by most tests."""
    return tmp_path / "tasks.json"


@pytest.fixture
def cli(data_file, tmp_path):
    """Run the CLI against the temporary data file."""

    def run(*args):
        return run_process(["--data-file", str(data_file), *args], tmp_path)

    return run


@pytest.fixture
def make_store(data_file):
    """Write a valid version-1 envelope directly, to set up a known state."""

    def make(tasks, next_id=None, path=None):
        target = path or data_file
        ids = [t["id"] for t in tasks]
        envelope = {
            "version": 1,
            "next_id": next_id if next_id is not None else max(ids, default=0) + 1,
            "tasks": tasks,
        }
        target.write_text(json.dumps(envelope), encoding="utf-8")
        return target

    return make
