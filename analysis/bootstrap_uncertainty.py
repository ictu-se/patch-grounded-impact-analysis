from __future__ import annotations

import csv
import random
import statistics
from collections import defaultdict
from pathlib import Path


CONDITION_ORDER = ["C0", "C1", "C2", "C3", "C4", "C5"]
ITERATIONS = 5000
SEED = 20260507


def read_trials(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def percentile(values: list[float], pct: float) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    position = (len(values) - 1) * pct
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def mean_quality(rows: list[dict[str, object]]) -> float:
    return statistics.fmean(float(row["operational_quality"]) for row in rows)


def cluster_bootstrap(rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rng = random.Random(SEED)
    by_condition_task: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_condition_task[str(row["condition"])][str(row["task_id"])].append(row)

    sampled_quality: dict[str, list[float]] = {condition: [] for condition in CONDITION_ORDER}
    sampled_rank: dict[str, list[int]] = {condition: [] for condition in CONDITION_ORDER}
    sampled_diffs: dict[str, list[float]] = {
        "C5_minus_C2": [],
        "C1_minus_C2": [],
        "C5_minus_C4": [],
        "C0_minus_C4": [],
    }

    task_ids_by_condition = {
        condition: sorted(tasks)
        for condition, tasks in by_condition_task.items()
    }

    for _ in range(ITERATIONS):
        draw_quality: dict[str, float] = {}
        for condition in CONDITION_ORDER:
            task_ids = task_ids_by_condition[condition]
            sampled_rows: list[dict[str, object]] = []
            for task_id in (rng.choice(task_ids) for _ in task_ids):
                sampled_rows.extend(by_condition_task[condition][task_id])
            value = mean_quality(sampled_rows)
            draw_quality[condition] = value
            sampled_quality[condition].append(value)

        ranked = sorted(draw_quality.items(), key=lambda item: item[1], reverse=True)
        for rank, (condition, _) in enumerate(ranked, start=1):
            sampled_rank[condition].append(rank)

        sampled_diffs["C5_minus_C2"].append(draw_quality["C5"] - draw_quality["C2"])
        sampled_diffs["C1_minus_C2"].append(draw_quality["C1"] - draw_quality["C2"])
        sampled_diffs["C5_minus_C4"].append(draw_quality["C5"] - draw_quality["C4"])
        sampled_diffs["C0_minus_C4"].append(draw_quality["C0"] - draw_quality["C4"])

    condition_rows: list[dict[str, object]] = []
    for condition in CONDITION_ORDER:
        values = sampled_quality[condition]
        ranks = sampled_rank[condition]
        condition_rows.append(
            {
                "condition": condition,
                "mean_quality": round(mean_quality([row for row in rows if row["condition"] == condition]), 3),
                "bootstrap_mean": round(statistics.fmean(values), 3),
                "ci95_low": round(percentile(values, 0.025), 3),
                "ci95_high": round(percentile(values, 0.975), 3),
                "rank_median": round(percentile([float(rank) for rank in ranks], 0.5), 1),
                "rank_low": int(percentile([float(rank) for rank in ranks], 0.025)),
                "rank_high": int(percentile([float(rank) for rank in ranks], 0.975)),
                "top2_probability": round(sum(rank <= 2 for rank in ranks) / len(ranks), 3),
                "bottom2_probability": round(sum(rank >= 5 for rank in ranks) / len(ranks), 3),
            }
        )

    diff_rows: list[dict[str, object]] = []
    for comparison, values in sampled_diffs.items():
        diff_rows.append(
            {
                "comparison": comparison,
                "mean_diff": round(statistics.fmean(values), 3),
                "ci95_low": round(percentile(values, 0.025), 3),
                "ci95_high": round(percentile(values, 0.975), 3),
                "positive_probability": round(sum(value > 0 for value in values) / len(values), 3),
            }
        )
    return condition_rows, diff_rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "analysis" / "outputs"
    rows = read_trials(out_dir / "se_surface_trials.csv")
    condition_rows, diff_rows = cluster_bootstrap(rows)
    write_csv(
        out_dir / "se_surface_bootstrap_condition_ci.csv",
        [
            "condition",
            "mean_quality",
            "bootstrap_mean",
            "ci95_low",
            "ci95_high",
            "rank_median",
            "rank_low",
            "rank_high",
            "top2_probability",
            "bottom2_probability",
        ],
        condition_rows,
    )
    write_csv(
        out_dir / "se_surface_bootstrap_differences.csv",
        ["comparison", "mean_diff", "ci95_low", "ci95_high", "positive_probability"],
        diff_rows,
    )
    print(f"bootstrap_iterations={ITERATIONS}")
    for row in condition_rows:
        print(
            f"{row['condition']} mean={row['mean_quality']} "
            f"ci=[{row['ci95_low']}, {row['ci95_high']}] "
            f"top2={row['top2_probability']} bottom2={row['bottom2_probability']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
