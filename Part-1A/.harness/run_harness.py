"""Deterministic harness for Part 1A: lint, security and test gates.

Runs every gate (does not stop at the first failure) and records structured
evidence under evidence/harness-results/. Exit code 0 only if all gates pass.
Run from the project root with the virtual environment active:
    python .harness/run_harness.py
"""
import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evidence" / "harness-results"

GATES = [
    ("lint", [sys.executable, "-m", "ruff", "check", "src", "tests"]),
    # -ll reports medium and high severity only, matching the constitution.
    ("security", [sys.executable, "-m", "bandit", "-r", "src", "-ll", "-q"]),
    ("tests", [sys.executable, "-m", "pytest", "tests", "-q"]),
]


def run_gate(name, command):
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        code, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        code, out, err = 124, "", "Gate timed out after 1800 seconds."
    return {
        "gate": name,
        "command": " ".join(command[1:]),
        "exit_code": code,
        "status": "PASS" if code == 0 else "FAIL",
        "duration_seconds": round(time.perf_counter() - started, 2),
        "stdout": out,
        "stderr": err,
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results = [run_gate(name, command) for name, command in GATES]
    overall = "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL"

    report = {
        "timestamp": stamp,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "overall": overall,
        "gates": results,
    }
    (RESULTS_DIR / f"run-{stamp}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    lines = []
    for r in results:
        lines.append(f"=== {r['gate']}: {r['status']} (exit {r['exit_code']}) ===")
        lines.append(r["stdout"])
        lines.append(r["stderr"])
    lines.append(f"OVERALL: {overall}")
    text = "\n".join(lines)
    (RESULTS_DIR / f"run-{stamp}.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
