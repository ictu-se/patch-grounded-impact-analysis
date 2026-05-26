from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from build_surface_tables import (
    CORE_CONDITIONS,
    CONDITION_LABELS,
    PILOT_TASKS,
    is_core_factorial,
    load_metrics,
    score_trial,
)


DIMENSIONS = [
    "repair_validity",
    "target_faithfulness",
    "validation_discipline",
    "process_minimality",
    "instruction_alignment",
]

WEIGHT_SCHEMES = {
    "reported": {
        "repair_validity": 0.18,
        "target_faithfulness": 0.28,
        "validation_discipline": 0.18,
        "process_minimality": 0.18,
        "instruction_alignment": 0.18,
    },
    "equal": {
        "repair_validity": 0.20,
        "target_faithfulness": 0.20,
        "validation_discipline": 0.20,
        "process_minimality": 0.20,
        "instruction_alignment": 0.20,
    },
    "validity_heavy": {
        "repair_validity": 0.35,
        "target_faithfulness": 0.25,
        "validation_discipline": 0.15,
        "process_minimality": 0.125,
        "instruction_alignment": 0.125,
    },
    "target_heavy": {
        "repair_validity": 0.15,
        "target_faithfulness": 0.40,
        "validation_discipline": 0.15,
        "process_minimality": 0.15,
        "instruction_alignment": 0.15,
    },
    "process_alignment_heavy": {
        "repair_validity": 0.125,
        "target_faithfulness": 0.20,
        "validation_discipline": 0.125,
        "process_minimality": 0.275,
        "instruction_alignment": 0.275,
    },
    "validation_heavy": {
        "repair_validity": 0.15,
        "target_faithfulness": 0.20,
        "validation_discipline": 0.35,
        "process_minimality": 0.15,
        "instruction_alignment": 0.15,
    },
}


def mean(rows: list[dict[str, object]], field: str) -> float:
    return statistics.fmean(float(row[field]) for row in rows) if rows else 0.0


def weighted_quality(row: dict[str, object], weights: dict[str, float]) -> float:
    return sum(float(row[field]) * weight for field, weight in weights.items())


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_sensitivity(trials: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in trials:
        grouped[str(row["condition"])].append(row)

    rows: list[dict[str, object]] = []
    for scheme, weights in WEIGHT_SCHEMES.items():
        scored = []
        for condition in ["C0", "C1", "C2", "C3", "C4", "C5"]:
            group = grouped[condition]
            value = statistics.fmean(weighted_quality(row, weights) for row in group)
            scored.append((condition, round(value, 3)))
        ranked = sorted(scored, key=lambda item: item[1], reverse=True)
        for rank, (condition, value) in enumerate(ranked, start=1):
            rows.append(
                {
                    "scheme": scheme,
                    "rank": rank,
                    "condition": condition,
                    "quality": value,
                }
            )
    return rows


def summarize_rank_stability(sensitivity_rows: list[dict[str, object]]) -> dict[str, object]:
    top2_sets = []
    bottom2_sets = []
    ranks: dict[str, list[int]] = defaultdict(list)
    for scheme in WEIGHT_SCHEMES:
        scheme_rows = [row for row in sensitivity_rows if row["scheme"] == scheme]
        scheme_rows.sort(key=lambda row: int(row["rank"]))
        top2_sets.append(tuple(row["condition"] for row in scheme_rows[:2]))
        bottom2_sets.append(tuple(row["condition"] for row in scheme_rows[-2:]))
        for row in scheme_rows:
            ranks[str(row["condition"])].append(int(row["rank"]))

    return {
        "schemes": list(WEIGHT_SCHEMES),
        "top2_by_scheme": top2_sets,
        "bottom2_by_scheme": bottom2_sets,
        "top2_stable_as_set": len({frozenset(item) for item in top2_sets}) == 1,
        "bottom2_stable_as_set": len({frozenset(item) for item in bottom2_sets}) == 1,
        "rank_ranges": {
            condition: [min(values), max(values)]
            for condition, values in sorted(ranks.items())
        },
    }


def audit_label(row: dict[str, object]) -> dict[str, object]:
    passed = bool(row["evaluation_passed"])
    edits = int(row.get("file_edit_count", 0) or 0)
    commands = int(row.get("command_count", 0) or 0)
    patch_lines = int(row.get("patch_lines", 0) or 0)
    runtime = float(row.get("runtime_sec", 0.0) or 0.0)
    condition_id = str(row["condition_id"])
    files_touched = [str(path).replace("\\", "/") for path in row.get("files_touched", [])]
    no_edit_failure = not passed and edits == 0
    wrong_target = condition_id == "guidance_stale_skill_concise_medium" and any(
        "legacy/" in path for path in files_touched
    )

    target_ok = passed and not wrong_target
    validation_ok = commands > 0 and str(row.get("evaluation", {}).get("status", "")) == "completed"
    minimal_ok = edits <= 1 and patch_lines <= 16 and runtime <= 18 and not no_edit_failure
    alignment_ok = not wrong_target and not (
        condition_id == "guidance_verbose_skill_verbose_medium" and runtime > 18
    )
    if no_edit_failure:
        alignment_ok = False

    return {
        "audit_repair_valid": passed,
        "audit_target_faithful": target_ok,
        "audit_validation_disciplined": validation_ok,
        "audit_process_minimal": minimal_ok,
        "audit_instruction_aligned": alignment_ok,
        "audit_no_edit_failure": no_edit_failure,
        "audit_wrong_target": wrong_target,
    }


def select_audit_rows(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    candidates = [
        row
        for row in metrics
        if is_core_factorial(row)
        and str(row["task_id"]) in PILOT_TASKS
        and str(row["condition_id"]) in CORE_CONDITIONS
    ]
    selected: list[dict[str, object]] = []
    seen: set[str] = set()
    for condition_id in CORE_CONDITIONS:
        group = [row for row in candidates if str(row["condition_id"]) == condition_id]
        failed = [row for row in group if not bool(row["evaluation_passed"])]
        passed = [row for row in group if bool(row["evaluation_passed"])]
        priority = failed[:4] + passed[:6] + failed[4:] + passed[6:]
        for row in priority[:6]:
            job_id = str(row["job_id"])
            if job_id not in seen:
                selected.append(row)
                seen.add(job_id)
    return selected


def summarize_audit(audit_rows: list[dict[str, object]]) -> dict[str, object]:
    dimensions = {
        "repair_validity": "audit_repair_valid",
        "target_faithfulness": "audit_target_faithful",
        "validation_discipline": "audit_validation_disciplined",
        "process_minimality": "audit_process_minimal",
        "instruction_alignment": "audit_instruction_aligned",
    }
    agreement = {}
    for score_field, label_field in dimensions.items():
        matches = 0
        for row in audit_rows:
            score_positive = float(row[score_field]) >= 0.65
            label_positive = str(row[label_field]).lower() == "true"
            if score_positive == label_positive:
                matches += 1
        agreement[score_field] = round(matches / len(audit_rows), 3)
    return {
        "audited_trials": len(audit_rows),
        "no_edit_failures": sum(str(row["audit_no_edit_failure"]).lower() == "true" for row in audit_rows),
        "wrong_target_failures": sum(str(row["audit_wrong_target"]).lower() == "true" for row in audit_rows),
        "threshold_agreement_at_0_65": agreement,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "analysis" / "outputs"
    metrics = load_metrics(root / "runs" / "metrics")
    core_metrics = [row for row in metrics if is_core_factorial(row)]
    core_trials = [score_trial(row) for row in core_metrics]

    sensitivity_rows = summarize_sensitivity(core_trials)
    write_csv(
        out_dir / "se_surface_sensitivity.csv",
        ["scheme", "rank", "condition", "quality"],
        sensitivity_rows,
    )
    stability_report = summarize_rank_stability(sensitivity_rows)
    (out_dir / "se_surface_sensitivity_report.json").write_text(
        json.dumps(stability_report, indent=2) + "\n",
        encoding="utf-8",
    )

    audit_metrics = select_audit_rows(core_metrics)
    score_by_job = {str(row["job_id"]): row for row in core_trials}
    audit_rows: list[dict[str, object]] = []
    for row in audit_metrics:
        scored = score_by_job[str(row["job_id"])]
        labels = audit_label(row)
        audit_rows.append(
            {
                "job_id": row["job_id"],
                "task_id": row["task_id"],
                "condition": CONDITION_LABELS[str(row["condition_id"])],
                "passed": row["evaluation_passed"],
                "file_edit_count": row.get("file_edit_count", 0),
                "command_count": row.get("command_count", 0),
                "patch_lines": row.get("patch_lines", 0),
                "files_touched": ";".join(str(path) for path in row.get("files_touched", [])),
                **{field: scored[field] for field in [*DIMENSIONS, "operational_quality"]},
                **labels,
            }
        )
    write_csv(
        out_dir / "se_surface_artifact_audit.csv",
        [
            "job_id",
            "task_id",
            "condition",
            "passed",
            "file_edit_count",
            "command_count",
            "patch_lines",
            "files_touched",
            *DIMENSIONS,
            "operational_quality",
            "audit_repair_valid",
            "audit_target_faithful",
            "audit_validation_disciplined",
            "audit_process_minimal",
            "audit_instruction_aligned",
            "audit_no_edit_failure",
            "audit_wrong_target",
        ],
        audit_rows,
    )
    audit_report = summarize_audit(audit_rows)
    (out_dir / "se_surface_artifact_audit_report.json").write_text(
        json.dumps(audit_report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"sensitivity_schemes={len(WEIGHT_SCHEMES)}")
    print(f"top2_stable={stability_report['top2_stable_as_set']}")
    print(f"bottom2_stable={stability_report['bottom2_stable_as_set']}")
    print(f"audited_trials={audit_report['audited_trials']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
