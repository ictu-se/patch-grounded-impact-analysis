from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


DEFAULT_MODELS = [
    "qwen2.5-coder:7b",
    "qwen2.5-coder:3b",
    "qwen2.5:7b",
    "granite-code:3b",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a stability leaderboard from repeated runs.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--condition-id",
        default="guidance_minimal_skill_concise_medium",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=None,
    )
    return parser.parse_args()


def load_rows(metrics_dir: Path) -> list[dict[str, object]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(metrics_dir.glob("*.json"))]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    metrics_dir = root / "runs" / "metrics"
    out_dir = root / "analysis" / "outputs"
    selected_models = args.model or DEFAULT_MODELS

    rows = []
    for row in load_rows(metrics_dir):
        if str(row.get("task_id", "")).startswith("demo_"):
            continue
        if row.get("condition_id") != args.condition_id:
            continue
        model_id = str(row.get("model_id", ""))
        if model_id not in selected_models:
            continue
        rows.append(row)

    by_model: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_model_task: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        model_id = str(row["model_id"])
        task_id = str(row["task_id"])
        by_model[model_id].append(row)
        by_model_task[(model_id, task_id)].append(row)

    leaderboard_rows: list[dict[str, object]] = []
    for model_id in selected_models:
        model_rows = by_model.get(model_id, [])
        if not model_rows:
            continue
        total_runs = len(model_rows)
        total_passed = sum(1 for row in model_rows if row["evaluation_passed"] is True)
        avg_runtime = sum(float(row["runtime_sec"]) for row in model_rows) / total_runs
        no_edit_fail = sum(
            1
            for row in model_rows
            if row["evaluation_passed"] is not True and int(row.get("file_edit_count", 0)) == 0
        )
        task_success_rates = []
        task_perfect = 0
        for (row_model, task_id), task_rows in sorted(by_model_task.items()):
            if row_model != model_id:
                continue
            task_runs = len(task_rows)
            task_passed = sum(1 for row in task_rows if row["evaluation_passed"] is True)
            rate = task_passed / task_runs if task_runs else 0.0
            task_success_rates.append(rate)
            if rate == 1.0:
                task_perfect += 1
        task_success_rates.sort()
        median_task_rate = (
            task_success_rates[len(task_success_rates) // 2]
            if task_success_rates
            else 0.0
        )
        leaderboard_rows.append(
            {
                "model_id": model_id,
                "runs": total_runs,
                "passed_runs": total_passed,
                "pass_rate": round(total_passed / total_runs, 4),
                "avg_runtime_sec": round(avg_runtime, 4),
                "perfect_tasks": task_perfect,
                "median_task_success_rate": round(median_task_rate, 4),
                "no_edit_failures": no_edit_fail,
            }
        )

    leaderboard_rows.sort(
        key=lambda row: (
            row["pass_rate"],
            row["perfect_tasks"],
            -row["avg_runtime_sec"],
        ),
        reverse=True,
    )

    csv_path = out_dir / "stability_leaderboard.csv"
    write_csv(
        csv_path,
        [
            "model_id",
            "runs",
            "passed_runs",
            "pass_rate",
            "avg_runtime_sec",
            "perfect_tasks",
            "median_task_success_rate",
            "no_edit_failures",
        ],
        leaderboard_rows,
    )

    report_lines = [
        "# Stability Leaderboard",
        "",
        f"Condition analyzed: `{args.condition_id}`",
        "",
        "| Model | Runs | Passed Runs | Pass Rate | Avg Runtime (s) | Perfect Tasks | Median Task Success | No-Edit Failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in leaderboard_rows:
        report_lines.append(
            f"| {row['model_id']} | {row['runs']} | {row['passed_runs']} | {row['pass_rate']:.2%} | "
            f"{row['avg_runtime_sec']} | {row['perfect_tasks']} | {row['median_task_success_rate']:.2%} | "
            f"{row['no_edit_failures']} |"
        )

    report_path = out_dir / "stability_leaderboard.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"wrote={csv_path}")
    print(f"wrote={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
