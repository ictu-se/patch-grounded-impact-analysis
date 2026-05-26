from __future__ import annotations

from pathlib import Path


def is_job_complete(metrics_dir: Path, job_id: str) -> bool:
    return (metrics_dir / f"{job_id}.json").exists()
