from __future__ import annotations

from pathlib import Path

from .models import ConditionSpec


def inject_condition_assets(
    condition: ConditionSpec,
    benchmark_root: Path,
    workspace: Path,
) -> dict[str, str]:
    injected: dict[str, str] = {}

    guidance_map = {
        "minimal": benchmark_root / "guidance_templates" / "minimal.md",
        "verbose": benchmark_root / "guidance_templates" / "verbose.md",
        "stale/conflicting": benchmark_root / "guidance_templates" / "stale_conflicting.md",
    }
    skill_map = {
        "concise_task_skill": benchmark_root / "skills" / "concise_task_skill.md",
        "verbose_process_skill": benchmark_root / "skills" / "verbose_process_skill.md",
    }

    guidance_src = guidance_map.get(condition.guidance_mode)
    if guidance_src and guidance_src.exists():
        target = workspace / "AGENTS.md"
        target.write_text(guidance_src.read_text(encoding="utf-8"), encoding="utf-8")
        injected["guidance_file"] = str(target)

    skill_src = skill_map.get(condition.skill_mode)
    if skill_src and skill_src.exists():
        target = workspace / "SKILL.md"
        target.write_text(skill_src.read_text(encoding="utf-8"), encoding="utf-8")
        injected["skill_file"] = str(target)

    return injected
