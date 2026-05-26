from __future__ import annotations

import os
import time
from datetime import datetime, UTC
from pathlib import Path

from .agents.mock_agent import run_mock_agent
from .agents.ollama_agent import run_ollama_agent
from .condition_injector import inject_condition_assets
from .models import JobSpec
from .telemetry import write_json
from .test_evaluator import evaluate_task
from .workspace_manager import prepare_workspace


def apply_file_writes(workspace: Path, file_writes: dict[str, str]) -> list[str]:
    written_files: list[str] = []
    for relative_path, content in file_writes.items():
        target = (workspace / relative_path).resolve()
        if workspace.resolve() not in target.parents and target != workspace.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written_files.append(str(target.relative_to(workspace)))
    return written_files


def execute_job(job: JobSpec, benchmark_root: Path, runs_root: Path) -> dict[str, object]:
    started = time.perf_counter()
    started_at = datetime.now(UTC).isoformat()

    workspace = prepare_workspace(job, runs_root / "checkpoints" / "workspaces")
    injected = inject_condition_assets(job.condition, benchmark_root, workspace)

    backend = os.environ.get("AGENT_BACKEND", "mock").strip().lower()
    if backend == "ollama":
        agent_result = run_ollama_agent(job, workspace, model=job.model_id or None)
    else:
        agent_result = run_mock_agent(job, workspace)

    written_files = apply_file_writes(workspace, agent_result.file_writes)
    merged_files_touched = sorted(set(agent_result.files_touched + written_files))
    evaluation = evaluate_task(job.task, workspace)

    runtime_sec = round(time.perf_counter() - started, 4)
    patch_path = runs_root / "patches" / f"{job.job_id}.patch"
    patch_path.write_text(agent_result.patch_text, encoding="utf-8")

    trajectory_path = runs_root / "trajectories" / f"{job.job_id}.json"
    write_json(
        trajectory_path,
        {
            "job_id": job.job_id,
            "trajectory": agent_result.trajectory,
            "summary": agent_result.summary,
        },
    )

    finished_at = datetime.now(UTC).isoformat()
    return {
        "job_id": job.job_id,
        "task_id": job.task.task_id,
        "condition_id": job.condition.condition_id,
        "model_id": job.model_id or agent_result.metadata.get("model", ""),
        "retry_index": job.retry_index,
        "status": agent_result.status,
        "evaluation_passed": evaluation.get("passed", False),
        "runtime_sec": runtime_sec,
        "command_count": len(agent_result.commands),
        "file_edit_count": len(merged_files_touched),
        "patch_lines": len(agent_result.patch_text.splitlines()),
        "failure_label": "" if agent_result.status == "success" else "agent_failed",
        "started_at": started_at,
        "finished_at": finished_at,
        "workspace": str(workspace),
        "injected": injected,
        "commands": agent_result.commands,
        "files_touched": merged_files_touched,
        "file_writes": agent_result.file_writes,
        "agent_summary": agent_result.summary,
        "agent_metadata": agent_result.metadata,
        "evaluation": evaluation,
    }
