from __future__ import annotations

import shutil
from pathlib import Path

from .models import JobSpec


def prepare_workspace(job: JobSpec, workspace_root: Path) -> Path:
    workspace_root.mkdir(parents=True, exist_ok=True)
    job_workspace = workspace_root / job.job_id
    if job_workspace.exists():
        shutil.rmtree(job_workspace)
    job_workspace.mkdir(parents=True, exist_ok=True)
    source_repo = job.root_dir / "benchmark" / job.task.repo_path
    if source_repo.exists():
        shutil.copytree(source_repo, job_workspace, dirs_exist_ok=True)
    return job_workspace
