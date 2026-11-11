"""AC-20 / NFR-003: list performance over 10,000 tasks.

Median of five full CLI runs (process launch through complete stdout capture)
must be at most 2 seconds, for both an unfiltered and a tag-filtered list.
The machine's OS, CPU, memory and Python version are recorded with the result.
"""

import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from conftest import run_process

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evidence" / "harness-results"
TASK_COUNT = 10_000
RUNS = 5
LIMIT_SECONDS = 2.0


def _total_memory_gb():
    """Best-effort total physical memory in GB (None if it cannot be determined)."""
    try:
        if sys.platform == "win32":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / 1024**3, 1)
        with open("/proc/meminfo", encoding="utf-8") as handle:
            first_line = handle.readline()
        return round(int(first_line.split()[1]) / 1024**2, 1)
    except (OSError, ValueError, AttributeError, IndexError):
        return None


def _build_tasks():
    priorities = ["low", "medium", "high"]
    tasks = []
    for number in range(1, TASK_COUNT + 1):
        tasks.append(
            {
                "id": number,
                "title": f"Task {number}",
                "priority": priorities[number % 3],
                "tags": ["bench"] if number % 4 == 0 else ["other"],
                "status": "todo",
            }
        )
    return tasks


def _time_runs(args, tmp_path):
    durations = []
    last = None
    for _ in range(RUNS):
        start = time.perf_counter()
        last = run_process(args, tmp_path)
        durations.append(time.perf_counter() - start)
        assert last.code == 0
        assert last.err == ""
    return durations, last


def test_ac20_ten_thousand_task_lists_meet_two_second_median(tmp_path):
    """AC-20: unfiltered and tag-filtered list medians are at most 2 seconds."""
    assert sys.version_info[:2] == (3, 12), "AC-20 is measured under Python 3.12"

    data_file = tmp_path / "big.json"
    envelope = {"version": 1, "next_id": TASK_COUNT + 1, "tasks": _build_tasks()}
    data_file.write_text(json.dumps(envelope), encoding="utf-8")

    unfiltered_times, unfiltered = _time_runs(["--data-file", str(data_file), "list"], tmp_path)
    filtered_times, filtered = _time_runs(
        ["--data-file", str(data_file), "list", "--tag", "bench"], tmp_path
    )

    # Sanity: the timed commands really returned the full, correct results.
    assert len(json.loads(unfiltered.out)) == TASK_COUNT
    assert len(json.loads(filtered.out)) == TASK_COUNT // 4

    unfiltered_median = statistics.median(unfiltered_times)
    filtered_median = statistics.median(filtered_times)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "os": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "memory_gb": _total_memory_gb(),
        "task_count": TASK_COUNT,
        "runs": RUNS,
        "limit_seconds": LIMIT_SECONDS,
        "unfiltered_seconds": [round(value, 3) for value in unfiltered_times],
        "filtered_seconds": [round(value, 3) for value in filtered_times],
        "unfiltered_median": round(unfiltered_median, 3),
        "filtered_median": round(filtered_median, 3),
    }
    (RESULTS_DIR / "performance.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    assert unfiltered_median <= LIMIT_SECONDS
    assert filtered_median <= LIMIT_SECONDS
