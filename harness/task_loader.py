from __future__ import annotations

import json
from pathlib import Path

from .models import ConditionSpec, TaskSpec


def load_tasks(path: Path) -> list[TaskSpec]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [TaskSpec(**item) for item in data]


def load_conditions(path: Path) -> list[ConditionSpec]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ConditionSpec(**item) for item in data]
