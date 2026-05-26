from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any


@dataclass(slots=True)
class TaskSpec:
    task_id: str
    repo_name: str
    repo_path: str
    description: str
    evaluation: dict[str, Any]
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConditionSpec:
    condition_id: str
    guidance_mode: str
    skill_mode: str
    autonomy_mode: str
    max_steps: int
    max_commands: int
    allow_network: bool
    retry_budget: int


@dataclass(slots=True)
class AgentRunResult:
    status: str
    summary: str
    commands: list[str]
    files_touched: list[str]
    file_writes: dict[str, str]
    patch_text: str
    trajectory: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JobSpec:
    task: TaskSpec
    condition: ConditionSpec
    retry_index: int
    root_dir: Path
    model_id: str = ""

    @property
    def model_tag(self) -> str:
        if not self.model_id:
            return "default_model"
        return re.sub(r"[^a-zA-Z0-9]+", "_", self.model_id).strip("_").lower()

    @property
    def job_id(self) -> str:
        return (
            f"{self.task.task_id}__{self.condition.condition_id}__"
            f"{self.model_tag}__r{self.retry_index}"
        )
