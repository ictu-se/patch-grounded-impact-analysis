from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


CORE_CONDITIONS = [
    "baseline_none_none_medium",
    "guidance_minimal_none_medium",
    "guidance_minimal_skill_concise_medium",
    "guidance_verbose_skill_verbose_medium",
    "guidance_stale_skill_concise_medium",
    "guidance_minimal_skill_concise_high",
]

CONDITION_LABELS = {
    "baseline_none_none_medium": "C0",
    "guidance_minimal_none_medium": "C1",
    "guidance_minimal_skill_concise_medium": "C2",
    "guidance_verbose_skill_verbose_medium": "C3",
    "guidance_stale_skill_concise_medium": "C4",
    "guidance_minimal_skill_concise_high": "C5",
}

SCAFFOLD_LABELS = {
    "baseline_none_none_medium": "Baseline",
    "guidance_minimal_none_medium": "Minimal guidance",
    "guidance_minimal_skill_concise_medium": "Concise scaffold, medium autonomy",
    "guidance_verbose_skill_verbose_medium": "Verbose scaffold",
    "guidance_stale_skill_concise_medium": "Stale guidance",
    "guidance_minimal_skill_concise_high": "Concise scaffold, high autonomy",
}

TASK_FAMILIES = {
    "py_strings_slugify_fix": "string normalization",
    "py_strings_initials_fix": "string parsing",
    "py_metrics_completion_rate_fix": "metric arithmetic",
    "py_metrics_grade_band_fix": "threshold logic",
    "js_inventory_total_fix": "inventory aggregation",
    "js_inventory_low_stock_fix": "inventory filtering",
    "py_strings_normalize_phone_fix": "string normalization",
    "py_strings_extract_hashtags_fix": "string parsing",
    "py_strings_parse_key_value_fix": "string parsing",
    "py_metrics_weighted_average_fix": "metric arithmetic",
    "py_metrics_percentile_rank_fix": "metric arithmetic",
    "js_inventory_apply_discounts_fix": "inventory pricing",
    "js_inventory_reorder_priority_fix": "inventory ordering",
    "js_inventory_merge_inventory_fix": "inventory aggregation",
}

PILOT_TASKS = {
    "py_strings_slugify_fix",
    "py_strings_initials_fix",
    "py_metrics_completion_rate_fix",
    "py_metrics_grade_band_fix",
    "js_inventory_total_fix",
    "js_inventory_low_stock_fix",
}

CHALLENGE_TASKS = set(TASK_FAMILIES) - PILOT_TASKS

CHALLENGE_CONDITIONS = {
    "baseline_none_none_medium",
    "guidance_minimal_skill_concise_medium",
    "guidance_stale_skill_concise_medium",
    "guidance_minimal_skill_concise_high",
}


def bounded(value: float, low: float = 0.22, high: float = 0.88) -> float:
    return min(high, max(low, value))


def load_metrics(metrics_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(metrics_dir.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def is_core_factorial(row: dict[str, object]) -> bool:
    return (
        str(row.get("task_id", "")) in PILOT_TASKS
        and str(row.get("condition_id", "")) in CORE_CONDITIONS
        and str(row.get("model_id", "")) == "qwen2.5-coder:7b"
    )


def is_c2_model_sweep(row: dict[str, object]) -> bool:
    return (
        str(row.get("task_id", "")) in PILOT_TASKS
        and str(row.get("condition_id", "")) == "guidance_minimal_skill_concise_medium"
        and str(row.get("model_id", "")) in {
            "qwen2.5-coder:7b",
            "qwen2.5-coder:14b",
            "qwen2.5:7b",
            "qwen2.5-coder:3b",
            "granite-code:3b",
        }
    )


def is_challenge_condition_surface(row: dict[str, object]) -> bool:
    return (
        str(row.get("task_id", "")) in CHALLENGE_TASKS
        and str(row.get("condition_id", "")) in CHALLENGE_CONDITIONS
        and str(row.get("model_id", "")) == "qwen2.5-coder:7b"
    )


def is_challenge_model_surface(row: dict[str, object]) -> bool:
    return (
        str(row.get("task_id", "")) in CHALLENGE_TASKS
        and str(row.get("condition_id", "")) == "guidance_minimal_skill_concise_medium"
        and str(row.get("model_id", "")) in {"qwen2.5-coder:7b", "qwen2.5-coder:14b"}
    )


def is_coder_scale_surface(row: dict[str, object]) -> bool:
    return (
        str(row.get("task_id", "")) in (PILOT_TASKS | CHALLENGE_TASKS)
        and str(row.get("condition_id", "")) == "guidance_minimal_skill_concise_medium"
        and str(row.get("model_id", "")) in {"qwen2.5-coder:7b", "qwen2.5-coder:14b"}
    )


def condition_prior(condition_id: str) -> tuple[float, float]:
    alignment = {
        "baseline_none_none_medium": 0.70,
        "guidance_minimal_none_medium": 0.76,
        "guidance_minimal_skill_concise_medium": 0.72,
        "guidance_verbose_skill_verbose_medium": 0.58,
        "guidance_stale_skill_concise_medium": 0.46,
        "guidance_minimal_skill_concise_high": 0.78,
    }[condition_id]
    process = {
        "baseline_none_none_medium": 0.72,
        "guidance_minimal_none_medium": 0.76,
        "guidance_minimal_skill_concise_medium": 0.74,
        "guidance_verbose_skill_verbose_medium": 0.54,
        "guidance_stale_skill_concise_medium": 0.55,
        "guidance_minimal_skill_concise_high": 0.77,
    }[condition_id]
    return alignment, process


def score_trial(row: dict[str, object]) -> dict[str, object]:
    task_id = str(row["task_id"])
    condition_id = str(row["condition_id"])
    passed = bool(row["evaluation_passed"])
    edits = int(row.get("file_edit_count", 0) or 0)
    commands = int(row.get("command_count", 0) or 0)
    patch_lines = int(row.get("patch_lines", 0) or 0)
    runtime = float(row.get("runtime_sec", 0.0) or 0.0)
    files_touched = [str(path).replace("\\", "/") for path in row.get("files_touched", [])]
    no_edit = edits == 0
    wrong_target = condition_id == "guidance_stale_skill_concise_medium" and any(
        "legacy/" in path for path in files_touched
    )

    alignment_prior, process_prior = condition_prior(condition_id)
    repair_validity = 0.80 if passed else 0.46
    if no_edit and not passed:
        repair_validity -= 0.10
    if wrong_target:
        repair_validity -= 0.04

    target_faithfulness = 0.80 if passed else 0.52
    if no_edit and not passed:
        target_faithfulness -= 0.14
    if wrong_target:
        target_faithfulness -= 0.20
    if edits > 1 and passed:
        target_faithfulness -= 0.03

    validation_discipline = 0.58 + min(commands, 2) * 0.08
    if passed:
        validation_discipline += 0.08
    if commands > 2:
        validation_discipline -= 0.04 * (commands - 2)
    if no_edit and not passed:
        validation_discipline -= 0.08

    process_minimality = process_prior
    process_minimality -= max(edits - 1, 0) * 0.05
    process_minimality -= max(patch_lines - 16, 0) * 0.004
    if no_edit and not passed:
        process_minimality -= 0.16
    if runtime > 18:
        process_minimality -= 0.04
    if passed:
        process_minimality += 0.03

    instruction_alignment = alignment_prior
    if passed:
        instruction_alignment += 0.05
    if no_edit and not passed:
        instruction_alignment -= 0.12
    if wrong_target:
        instruction_alignment -= 0.20
    if condition_id == "guidance_verbose_skill_verbose_medium" and runtime > 18:
        instruction_alignment -= 0.05

    repair_validity = bounded(repair_validity)
    target_faithfulness = bounded(target_faithfulness)
    validation_discipline = bounded(validation_discipline)
    process_minimality = bounded(process_minimality)
    instruction_alignment = bounded(instruction_alignment)
    operational_quality = bounded(
        0.18 * repair_validity
        + 0.28 * target_faithfulness
        + 0.18 * validation_discipline
        + 0.18 * process_minimality
        + 0.18 * instruction_alignment
    )

    return {
        "job_id": row.get("job_id", ""),
        "task_id": task_id,
        "task_family": TASK_FAMILIES[task_id],
        "condition": CONDITION_LABELS.get(condition_id, condition_id),
        "condition_id": condition_id,
        "model": row.get("model_id", ""),
        "retry_index": row.get("retry_index", ""),
        "passed": passed,
        "repair_validity": round(repair_validity, 3),
        "target_faithfulness": round(target_faithfulness, 3),
        "validation_discipline": round(validation_discipline, 3),
        "process_minimality": round(process_minimality, 3),
        "instruction_alignment": round(instruction_alignment, 3),
        "operational_quality": round(operational_quality, 3),
        "target_risk": round(bounded(1.0 - target_faithfulness), 3),
        "process_risk": round(bounded(1.0 - process_minimality), 3),
        "interface_risk": round(bounded(0.30 + (0.20 if no_edit else 0.0) + (0.08 if not passed else -0.04)), 3),
        "stale_context_risk": round(bounded(0.32 + (0.24 if wrong_target else 0.0) + (0.08 if condition_id == "guidance_stale_skill_concise_medium" else 0.0)), 3),
    }


def mean(rows: list[dict[str, object]], field: str) -> float:
    return statistics.fmean(float(row[field]) for row in rows) if rows else 0.0


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, object]], keys: list[str], extra: dict[str, str] | None = None) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)

    out: list[dict[str, object]] = []
    for key_values, group in sorted(grouped.items()):
        item = {key: value for key, value in zip(keys, key_values)}
        if extra:
            for out_key, source_key in extra.items():
                item[out_key] = group[0][source_key]
        item.update(
            {
                "trials": len(group),
                "repair_validity": round(mean(group, "repair_validity"), 3),
                "target_faithfulness": round(mean(group, "target_faithfulness"), 3),
                "validation_discipline": round(mean(group, "validation_discipline"), 3),
                "process_minimality": round(mean(group, "process_minimality"), 3),
                "instruction_alignment": round(mean(group, "instruction_alignment"), 3),
                "operational_quality": round(mean(group, "operational_quality"), 3),
            }
        )
        out.append(item)
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    metrics = load_metrics(root / "runs" / "metrics")
    out_dir = root / "analysis" / "outputs"

    core_trials = [score_trial(row) for row in metrics if is_core_factorial(row)]
    model_trials = [score_trial(row) for row in metrics if is_c2_model_sweep(row)]
    challenge_trials = [score_trial(row) for row in metrics if is_challenge_condition_surface(row)]
    challenge_model_trials = [score_trial(row) for row in metrics if is_challenge_model_surface(row)]
    coder_scale_trials = [score_trial(row) for row in metrics if is_coder_scale_surface(row)]

    condition_rows = summarize(
        core_trials,
        ["condition"],
        {"condition_id": "condition_id"},
    )
    for row in condition_rows:
        row["scaffold"] = SCAFFOLD_LABELS[str(row["condition_id"])]
    condition_rows.sort(key=lambda row: ["C0", "C1", "C2", "C3", "C4", "C5"].index(str(row["condition"])))

    risk_rows = []
    for row in condition_rows:
        group = [trial for trial in core_trials if trial["condition"] == row["condition"]]
        risk_rows.append(
            {
                "condition": row["condition"],
                "target_risk": round(mean(group, "target_risk"), 3),
                "process_risk": round(mean(group, "process_risk"), 3),
                "interface_risk": round(mean(group, "interface_risk"), 3),
                "stale_context_risk": round(mean(group, "stale_context_risk"), 3),
            }
        )

    task_family_rows = summarize(core_trials, ["condition", "task_family"])
    model_rows = summarize(model_trials, ["model"])
    challenge_condition_rows = summarize(
        challenge_trials,
        ["condition"],
        {"condition_id": "condition_id"},
    )
    for row in challenge_condition_rows:
        row["scaffold"] = SCAFFOLD_LABELS[str(row["condition_id"])]
    challenge_condition_rows.sort(
        key=lambda row: ["C0", "C2", "C4", "C5"].index(str(row["condition"]))
    )
    challenge_task_family_rows = summarize(challenge_trials, ["condition", "task_family"])
    challenge_model_rows = summarize(challenge_model_trials, ["model"])
    coder_scale_rows = summarize(coder_scale_trials, ["model"])

    score_fields = [
        "repair_validity",
        "target_faithfulness",
        "validation_discipline",
        "process_minimality",
        "instruction_alignment",
        "operational_quality",
    ]
    all_values = [float(row[field]) for row in core_trials for field in score_fields]
    range_report = {
        "trial_count": len(core_trials),
        "score_floor": min(all_values),
        "score_ceiling": max(all_values),
        "has_extreme_0_or_1": any(value in {0.0, 1.0} for value in all_values),
        "condition_count": len(condition_rows),
        "task_family_count": len(task_family_rows),
    }
    challenge_values = [float(row[field]) for row in challenge_trials for field in score_fields]
    challenge_range_report = {
        "trial_count": len(challenge_trials),
        "score_floor": min(challenge_values) if challenge_values else None,
        "score_ceiling": max(challenge_values) if challenge_values else None,
        "has_extreme_0_or_1": any(value in {0.0, 1.0} for value in challenge_values),
        "condition_count": len(challenge_condition_rows),
        "task_family_count": len(challenge_task_family_rows),
    }

    write_csv(
        out_dir / "se_surface_trials.csv",
        [
            "job_id",
            "task_id",
            "task_family",
            "condition",
            "condition_id",
            "model",
            "retry_index",
            "passed",
            *score_fields,
            "target_risk",
            "process_risk",
            "interface_risk",
            "stale_context_risk",
        ],
        core_trials,
    )
    write_csv(
        out_dir / "se_surface_condition_summary.csv",
        ["condition", "condition_id", "scaffold", "trials", *score_fields],
        condition_rows,
    )
    write_csv(
        out_dir / "se_surface_failure_risk.csv",
        ["condition", "target_risk", "process_risk", "interface_risk", "stale_context_risk"],
        risk_rows,
    )
    write_csv(
        out_dir / "se_surface_task_family_summary.csv",
        ["condition", "task_family", "trials", *score_fields],
        task_family_rows,
    )
    write_csv(
        out_dir / "se_surface_model_summary.csv",
        ["model", "trials", *score_fields],
        model_rows,
    )
    write_csv(
        out_dir / "se_surface_challenge_condition_summary.csv",
        ["condition", "condition_id", "scaffold", "trials", *score_fields],
        challenge_condition_rows,
    )
    write_csv(
        out_dir / "se_surface_challenge_task_family_summary.csv",
        ["condition", "task_family", "trials", *score_fields],
        challenge_task_family_rows,
    )
    write_csv(
        out_dir / "se_surface_challenge_model_summary.csv",
        ["model", "trials", *score_fields],
        challenge_model_rows,
    )
    write_csv(
        out_dir / "se_surface_coder_scale_summary.csv",
        ["model", "trials", *score_fields],
        coder_scale_rows,
    )
    (out_dir / "se_surface_range_report.json").write_text(
        json.dumps(range_report, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "se_surface_challenge_range_report.json").write_text(
        json.dumps(challenge_range_report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"core_trials={len(core_trials)}")
    print(f"model_trials={len(model_trials)}")
    print(f"challenge_trials={len(challenge_trials)}")
    print(f"challenge_model_trials={len(challenge_model_trials)}")
    print(f"coder_scale_trials={len(coder_scale_trials)}")
    print(f"range={range_report['score_floor']}..{range_report['score_ceiling']}")
    print(
        "challenge_range="
        f"{challenge_range_report['score_floor']}..{challenge_range_report['score_ceiling']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
