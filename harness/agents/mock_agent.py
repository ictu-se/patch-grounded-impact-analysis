from __future__ import annotations

from pathlib import Path

from ..models import AgentRunResult, JobSpec


def run_mock_agent(job: JobSpec, workspace: Path) -> AgentRunResult:
    commands = ["rg --files", "python -c \"print('agent inspection complete')\""]
    files_touched = []
    patch_text = (
        f"--- a/README.md\n+++ b/README.md\n@@\n"
        f"+Mock patch note for job {job.job_id}\n"
    )
    trajectory = [
        {"step": 1, "action": "inspect_repo", "detail": "Enumerated likely files."},
        {"step": 2, "action": "plan_patch", "detail": f"Prepared patch plan under {job.condition.autonomy_mode} autonomy."},
        {"step": 3, "action": "summarize", "detail": "Saved mock patch and telemetry."},
    ]
    summary = (
        f"Mock agent completed {job.task.task_id} under {job.condition.condition_id}. "
        f"No real code edits were applied."
    )
    return AgentRunResult(
        status="success",
        summary=summary,
        commands=commands,
        files_touched=files_touched,
        file_writes={},
        patch_text=patch_text,
        trajectory=trajectory,
        metadata={"backend": "mock_agent"},
    )
