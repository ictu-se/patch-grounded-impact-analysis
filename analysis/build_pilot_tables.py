from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


CORE_CONDITIONS = {
    "baseline_none_none_medium",
    "guidance_minimal_none_medium",
    "guidance_minimal_skill_concise_medium",
    "guidance_verbose_skill_verbose_medium",
    "guidance_stale_skill_concise_medium",
    "guidance_minimal_skill_concise_high",
}


def load_metrics(metrics_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(metrics_dir.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def is_pilot_row(row: dict[str, object]) -> bool:
    task_id = str(row.get("task_id", ""))
    condition_id = str(row.get("condition_id", ""))
    model_id = str(row.get("model_id", ""))
    return (
        not task_id.startswith("demo_")
        and condition_id in CORE_CONDITIONS
        and model_id == "qwen2.5-coder:7b"
    )


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    metrics_dir = root / "runs" / "metrics"
    out_dir = root / "analysis" / "outputs"
    rows = [row for row in load_metrics(metrics_dir) if is_pilot_row(row)]

    task_condition_rows: list[dict[str, object]] = []
    for row in rows:
        task_condition_rows.append(
            {
                "task_id": row["task_id"],
                "condition_id": row["condition_id"],
                "model_id": row.get("model_id", row.get("agent_metadata", {}).get("model", "")),
                "passed": row["evaluation_passed"],
                "runtime_sec": row["runtime_sec"],
                "file_edit_count": row["file_edit_count"],
                "command_count": row["command_count"],
                "model": row.get("agent_metadata", {}).get("model", ""),
            }
        )

    by_condition: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_condition[str(row["condition_id"])].append(row)

    condition_summary_rows: list[dict[str, object]] = []
    for condition_id, condition_rows in sorted(by_condition.items()):
        total = len(condition_rows)
        passed = sum(1 for row in condition_rows if row["evaluation_passed"] is True)
        avg_runtime = sum(float(row["runtime_sec"]) for row in condition_rows) / total if total else 0.0
        avg_edits = sum(int(row["file_edit_count"]) for row in condition_rows) / total if total else 0.0
        condition_summary_rows.append(
            {
                "condition_id": condition_id,
                "tasks": total,
                "passed": passed,
                "pass_rate": round(passed / total, 4) if total else 0.0,
                "avg_runtime_sec": round(avg_runtime, 4),
                "avg_file_edit_count": round(avg_edits, 4),
            }
        )

    task_fields = [
        "task_id",
        "condition_id",
        "model_id",
        "passed",
        "runtime_sec",
        "file_edit_count",
        "command_count",
        "model",
    ]
    condition_fields = [
        "condition_id",
        "tasks",
        "passed",
        "pass_rate",
        "avg_runtime_sec",
        "avg_file_edit_count",
    ]

    task_csv = out_dir / "pilot_task_condition_table.csv"
    condition_csv = out_dir / "pilot_condition_summary.csv"
    write_csv(task_csv, task_fields, task_condition_rows)
    write_csv(condition_csv, condition_fields, condition_summary_rows)

    report_lines = [
        "# Track A Pilot Report",
        "",
        "## Condition Summary",
        "",
        "| Condition | Tasks | Passed | Pass Rate | Avg Runtime (s) | Avg File Edits |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in condition_summary_rows:
        report_lines.append(
            f"| {row['condition_id']} | {row['tasks']} | {row['passed']} | {row['pass_rate']:.2%} | "
            f"{row['avg_runtime_sec']} | {row['avg_file_edit_count']} |"
        )

    report_lines.extend(
        [
            "",
            "## Task-by-Condition Detail",
            "",
            "| Task | Condition | Passed | Runtime (s) | File Edits | Commands | Model |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in task_condition_rows:
        report_lines.append(
            f"| {row['task_id']} | {row['condition_id']} | {row['passed']} | {row['runtime_sec']} | "
            f"{row['file_edit_count']} | {row['command_count']} | {row['model']} |"
        )

    report_path = out_dir / "pilot_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"wrote={task_csv}")
    print(f"wrote={condition_csv}")
    print(f"wrote={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
