from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

from build_surface_tables import (
    CONDITION_LABELS,
    PILOT_TASKS,
    load_metrics,
    score_trial,
)


REPLICATION_CONDITIONS = {
    "baseline_none_none_medium",
    "guidance_minimal_skill_concise_medium",
    "guidance_stale_skill_concise_medium",
    "guidance_minimal_skill_concise_high",
}
FULL_CORE_CONDITIONS = {
    "baseline_none_none_medium",
    "guidance_minimal_none_medium",
    "guidance_minimal_skill_concise_medium",
    "guidance_verbose_skill_verbose_medium",
    "guidance_stale_skill_concise_medium",
    "guidance_minimal_skill_concise_high",
}

REPLICATION_MODELS = {"qwen2.5-coder:7b", "qwen2.5-coder:14b"}

SCORE_FIELDS = [
    "repair_validity",
    "target_faithfulness",
    "validation_discipline",
    "process_minimality",
    "instruction_alignment",
    "operational_quality",
]


def is_replication_row(row: dict[str, object]) -> bool:
    return (
        str(row.get("task_id", "")) in PILOT_TASKS
        and str(row.get("condition_id", "")) in REPLICATION_CONDITIONS
        and str(row.get("model_id", "")) in REPLICATION_MODELS
        and int(row.get("retry_index", 0) or 0) in {0, 1}
    )


def is_full_core_model_row(row: dict[str, object]) -> bool:
    return (
        str(row.get("task_id", "")) in PILOT_TASKS
        and str(row.get("condition_id", "")) in FULL_CORE_CONDITIONS
        and str(row.get("model_id", "")) in REPLICATION_MODELS
        and int(row.get("retry_index", 0) or 0) in {0, 1, 2, 3}
    )


def mean(rows: list[dict[str, object]], field: str) -> float:
    return statistics.fmean(float(row[field]) for row in rows) if rows else 0.0


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, object]], keys: list[str]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)

    out: list[dict[str, object]] = []
    for key_values, group in sorted(grouped.items()):
        item = {key: value for key, value in zip(keys, key_values)}
        item["trials"] = len(group)
        for field in SCORE_FIELDS:
            item[field] = round(mean(group, field), 3)
        out.append(item)
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "analysis" / "outputs"
    metrics = [row for row in load_metrics(root / "runs" / "metrics") if is_replication_row(row)]
    trials = [score_trial(row) for row in metrics]
    full_metrics = [row for row in load_metrics(root / "runs" / "metrics") if is_full_core_model_row(row)]
    full_trials = [score_trial(row) for row in full_metrics]

    condition_model_rows = summarize(trials, ["model", "condition"])
    condition_model_rows.sort(key=lambda row: (str(row["model"]), str(row["condition"])))

    model_rows = summarize(trials, ["model"])
    model_rows.sort(key=lambda row: str(row["model"]))

    write_csv(
        out_dir / "se_surface_model_replication_slice.csv",
        ["model", "condition", "trials", *SCORE_FIELDS],
        condition_model_rows,
    )
    write_csv(
        out_dir / "se_surface_model_replication_slice_summary.csv",
        ["model", "trials", *SCORE_FIELDS],
        model_rows,
    )
    full_condition_model_rows = summarize(full_trials, ["model", "condition"])
    full_condition_model_rows.sort(key=lambda row: (str(row["model"]), str(row["condition"])))
    full_model_rows = summarize(full_trials, ["model"])
    full_model_rows.sort(key=lambda row: str(row["model"]))
    write_csv(
        out_dir / "se_surface_model_full_core_condition.csv",
        ["model", "condition", "trials", *SCORE_FIELDS],
        full_condition_model_rows,
    )
    write_csv(
        out_dir / "se_surface_model_full_core_summary.csv",
        ["model", "trials", *SCORE_FIELDS],
        full_model_rows,
    )

    print(f"replication_trials={len(trials)}")
    for row in model_rows:
        print(f"{row['model']} trials={row['trials']} quality={row['operational_quality']}")
    print(f"full_core_model_trials={len(full_trials)}")
    for row in full_model_rows:
        print(f"full {row['model']} trials={row['trials']} quality={row['operational_quality']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
