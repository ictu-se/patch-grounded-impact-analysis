from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .models import TaskSpec


def evaluate_task(task: TaskSpec, cwd: Path) -> dict[str, object]:
    evaluation = task.evaluation
    if evaluation.get("type") != "command":
        return {"passed": False, "status": "unsupported_evaluator"}

    started = time.perf_counter()
    completed = subprocess.run(
        evaluation["command"],
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    return {
        "passed": completed.returncode == 0,
        "status": "completed",
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "duration_sec": round(elapsed, 4),
    }
