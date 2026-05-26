from __future__ import annotations

import argparse
import os
from pathlib import Path

from .models import JobSpec
from .resume_registry import is_job_complete
from .run_task import execute_job
from .task_loader import load_conditions, load_tasks
from .telemetry import append_summary_row, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the software engineering agent harness.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tasks", type=Path, default=None)
    parser.add_argument("--conditions", type=Path, default=None)
    parser.add_argument("--max-jobs", type=int, default=None)
    parser.add_argument("--task-id", action="append", default=None)
    parser.add_argument("--condition-id", action="append", default=None)
    parser.add_argument("--model", action="append", default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    benchmark_root = root / "benchmark"
    runs_root = root / "runs"
    tasks_path = args.tasks or benchmark_root / "tasks.json"
    conditions_path = args.conditions or root / "harness" / "configs" / "conditions.json"

    tasks = load_tasks(tasks_path)
    conditions = load_conditions(conditions_path)
    if args.task_id:
        selected_task_ids = set(args.task_id)
        tasks = [task for task in tasks if task.task_id in selected_task_ids]
    if args.condition_id:
        selected_condition_ids = set(args.condition_id)
        conditions = [condition for condition in conditions if condition.condition_id in selected_condition_ids]
    selected_models = args.model or []
    if not selected_models:
        env_model = os.environ.get("OLLAMA_MODEL", "").strip()
        selected_models = [env_model] if env_model else [""]
    metrics_dir = runs_root / "metrics"
    summary_path = metrics_dir / "summary_partial.csv"

    job_count = 0
    for task in tasks:
        for condition in conditions:
            for model_id in selected_models:
                for retry_index in range(condition.retry_budget):
                    job = JobSpec(
                        task=task,
                        condition=condition,
                        retry_index=retry_index,
                        root_dir=root,
                        model_id=model_id,
                    )
                    if not args.force and is_job_complete(metrics_dir, job.job_id):
                        print(f"[skip] {job.job_id}")
                        continue

                    print(f"[run] {job.job_id}")
                    result = execute_job(job, benchmark_root, runs_root)
                    write_json(metrics_dir / f"{job.job_id}.json", result)
                    append_summary_row(summary_path, result)
                    print(
                        f"[done] {job.job_id} | passed={result['evaluation_passed']} "
                        f"| runtime={result['runtime_sec']}s"
                    )

                    job_count += 1
                    if args.max_jobs is not None and job_count >= args.max_jobs:
                        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
