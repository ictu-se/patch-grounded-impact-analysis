from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


DEFAULT_MODELS = [
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "qwen2.5:7b",
    "qwen2.5-coder:1.5b",
    "qwen2.5-coder:3b",
    "qwen2.5-coder:7b",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build model comparison outputs from run metrics.")
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
        help="Optional model ids to include. Defaults to the Qwen base-vs-coder sweep.",
    )
    parser.add_argument(
        "--retry-index",
        type=int,
        default=0,
        help="Filter to a specific retry index. Defaults to the first run to keep the sweep comparable.",
    )
    return parser.parse_args()


def load_rows(metrics_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(metrics_dir.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def model_family(model_id: str) -> str:
    return "coder" if "coder" in model_id else "base"


def model_size(model_id: str) -> str:
    return model_id.split(":")[-1]


def size_to_float(size: str) -> float:
    return float(size.rstrip("bB"))


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
        if not row.get("model_id"):
            continue
        if int(row.get("retry_index", -1)) != args.retry_index:
            continue
        model_id = str(row.get("model_id") or row.get("agent_metadata", {}).get("model", ""))
        if model_id not in selected_models:
            continue
        rows.append(row)

    by_model: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        model_id = str(row.get("model_id") or row.get("agent_metadata", {}).get("model", ""))
        by_model[model_id].append(row)

    summary_rows: list[dict[str, object]] = []
    for model_id in sorted(by_model, key=lambda item: (size_to_float(model_size(item)), model_family(item), item)):
        model_rows = by_model[model_id]
        total = len(model_rows)
        passed = sum(1 for row in model_rows if row["evaluation_passed"] is True)
        avg_runtime = sum(float(row["runtime_sec"]) for row in model_rows) / total if total else 0.0
        avg_commands = sum(int(row["command_count"]) for row in model_rows) / total if total else 0.0
        avg_edits = sum(int(row["file_edit_count"]) for row in model_rows) / total if total else 0.0
        summary_rows.append(
            {
                "model_id": model_id,
                "family": model_family(model_id),
                "size": model_size(model_id),
                "tasks": total,
                "passed": passed,
                "pass_rate": round(passed / total, 4) if total else 0.0,
                "avg_runtime_sec": round(avg_runtime, 4),
                "avg_command_count": round(avg_commands, 4),
                "avg_file_edit_count": round(avg_edits, 4),
            }
        )

    pairwise_rows: list[dict[str, object]] = []
    sizes = sorted({model_size(model_id) for model_id in by_model}, key=size_to_float)
    for size in sizes:
        base_id = f"qwen2.5:{size}"
        coder_id = f"qwen2.5-coder:{size}"
        base_row = next((row for row in summary_rows if row["model_id"] == base_id), None)
        coder_row = next((row for row in summary_rows if row["model_id"] == coder_id), None)
        if not base_row or not coder_row:
            continue
        pairwise_rows.append(
            {
                "size": size,
                "base_model": base_id,
                "coder_model": coder_id,
                "base_pass_rate": base_row["pass_rate"],
                "coder_pass_rate": coder_row["pass_rate"],
                "pass_rate_delta_pp": round((coder_row["pass_rate"] - base_row["pass_rate"]) * 100, 2),
                "base_avg_runtime_sec": base_row["avg_runtime_sec"],
                "coder_avg_runtime_sec": coder_row["avg_runtime_sec"],
                "runtime_delta_sec": round(coder_row["avg_runtime_sec"] - base_row["avg_runtime_sec"], 4),
            }
        )

    summary_path = out_dir / "model_comparison_summary.csv"
    pairwise_path = out_dir / "model_comparison_base_vs_coder.csv"
    write_csv(
        summary_path,
        [
            "model_id",
            "family",
            "size",
            "tasks",
            "passed",
            "pass_rate",
            "avg_runtime_sec",
            "avg_command_count",
            "avg_file_edit_count",
        ],
        summary_rows,
    )
    write_csv(
        pairwise_path,
        [
            "size",
            "base_model",
            "coder_model",
            "base_pass_rate",
            "coder_pass_rate",
            "pass_rate_delta_pp",
            "base_avg_runtime_sec",
            "coder_avg_runtime_sec",
            "runtime_delta_sec",
        ],
        pairwise_rows,
    )

    report_lines = [
        "# Local Small-Model Comparison Report",
        "",
        f"Condition analyzed: `{args.condition_id}`",
        f"Retry index analyzed: `{args.retry_index}`",
        "",
        "## Model Summary",
        "",
        "| Model | Family | Size | Passed | Tasks | Pass Rate | Avg Runtime (s) | Avg Commands | Avg File Edits |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        report_lines.append(
            f"| {row['model_id']} | {row['family']} | {row['size']} | {row['passed']} | {row['tasks']} | "
            f"{row['pass_rate']:.2%} | {row['avg_runtime_sec']} | {row['avg_command_count']} | {row['avg_file_edit_count']} |"
        )

    report_lines.extend(
        [
            "",
            "## Base vs Coder at the Same Size",
            "",
            "| Size | Base Pass Rate | Coder Pass Rate | Delta (pp) | Base Runtime (s) | Coder Runtime (s) | Runtime Delta (s) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in pairwise_rows:
        report_lines.append(
            f"| {row['size']} | {row['base_pass_rate']:.2%} | {row['coder_pass_rate']:.2%} | "
            f"{row['pass_rate_delta_pp']} | {row['base_avg_runtime_sec']} | {row['coder_avg_runtime_sec']} | "
            f"{row['runtime_delta_sec']} |"
        )

    report_lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
        ]
    )
    if summary_rows:
        best = max(summary_rows, key=lambda row: (row["pass_rate"], -row["avg_runtime_sec"]))
        report_lines.append(
            f"- Best pass rate in this sweep: `{best['model_id']}` at `{best['pass_rate']:.2%}`."
        )
    for row in pairwise_rows:
        direction = (
            "higher than"
            if row["coder_pass_rate"] > row["base_pass_rate"]
            else "equal to"
            if row["coder_pass_rate"] == row["base_pass_rate"]
            else "lower than"
        )
        report_lines.append(
            f"- At `{row['size']}`, `{row['coder_model']}` pass rate is {direction} "
            f"`{row['base_model']}` ({row['coder_pass_rate']:.2%} vs {row['base_pass_rate']:.2%})."
        )

    report_path = out_dir / "model_comparison_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"wrote={summary_path}")
    print(f"wrote={pairwise_path}")
    print(f"wrote={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
