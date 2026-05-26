from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib import request

from ..models import AgentRunResult, JobSpec


def _build_prompt(job: JobSpec, workspace: Path) -> str:
    guidance_path = workspace / "AGENTS.md"
    skill_path = workspace / "SKILL.md"
    guidance = guidance_path.read_text(encoding="utf-8") if guidance_path.exists() else "None"
    skill = skill_path.read_text(encoding="utf-8") if skill_path.exists() else "None"
    repo_snapshot = build_repo_snapshot(workspace)
    return (
        "You are a coding agent running inside a software engineering experiment harness.\n"
        "Return valid JSON only.\n"
        "Use exactly these keys: summary, commands, files_touched, file_writes, patch_text, trajectory.\n"
        "Prefer the smallest viable fix.\n"
        "Only include file_writes for files you want to replace completely.\n"
        "Do not wrap the JSON in markdown or prose.\n\n"
        f"Task ID: {job.task.task_id}\n"
        f"Description: {job.task.description}\n"
        f"Autonomy mode: {job.condition.autonomy_mode}\n"
        f"Guidance mode: {job.condition.guidance_mode}\n"
        f"Skill mode: {job.condition.skill_mode}\n"
        f"Workspace: {workspace}\n"
        f"Guidance file contents:\n{guidance}\n\n"
        f"Skill file contents:\n{skill}\n"
        f"\nRepository snapshot:\n{repo_snapshot}\n"
    )


def build_repo_snapshot(workspace: Path) -> str:
    lines: list[str] = []
    for path in sorted(workspace.rglob("*")):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(workspace)
        if rel.name in {"AGENTS.md", "SKILL.md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if len(text) > 4000:
            text = text[:4000] + "\n... [truncated]"
        lines.append(f"FILE: {rel.as_posix()}\n{text}\n")
    return "\n".join(lines)


def run_ollama_agent(job: JobSpec, workspace: Path, model: str | None = None) -> AgentRunResult:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    model_name = model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
    timeout_sec = int(os.environ.get("OLLAMA_REQUEST_TIMEOUT_SEC", "900"))
    body = post_generate(
        host=host,
        timeout_sec=timeout_sec,
        payload={
            "model": model_name,
            "prompt": _build_prompt(job, workspace),
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "num_ctx": 4096,
                "num_predict": 700,
            },
        },
    )
    raw_text = body.get("response", "").strip()
    parsed, parse_meta = parse_agent_response(
        host=host,
        timeout_sec=timeout_sec,
        model_name=model_name,
        raw_text=raw_text,
    )

    file_writes = finalize_file_writes(
        parsed=parsed,
        files_touched=[str(item) for item in parsed.get("files_touched", [])],
        patch_text=str(parsed.get("patch_text", "")),
    )

    return AgentRunResult(
        status="success",
        summary=str(parsed.get("summary", "")),
        commands=[str(item) for item in parsed.get("commands", [])],
        files_touched=[str(item) for item in parsed.get("files_touched", [])],
        file_writes=file_writes,
        patch_text=str(parsed.get("patch_text", "")),
        trajectory=list(parsed.get("trajectory", [])),
        metadata={
            "backend": "ollama",
            "model": model_name,
            "eval_count": body.get("eval_count"),
            "eval_duration": body.get("eval_duration"),
            "load_duration": body.get("load_duration"),
            "prompt_eval_count": body.get("prompt_eval_count"),
            "prompt_eval_duration": body.get("prompt_eval_duration"),
            "parse_mode": parse_meta["mode"],
            "parse_repaired": parse_meta["repaired"],
            "raw_response_excerpt": raw_text[:400],
        },
    )


def post_generate(host: str, timeout_sec: int, payload: dict[str, object]) -> dict[str, object]:
    req = request.Request(
        f"{host}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_agent_response(
    host: str,
    timeout_sec: int,
    model_name: str,
    raw_text: str,
) -> tuple[dict[str, object], dict[str, object]]:
    cleaned_text = strip_code_fences(raw_text)
    parsed = try_parse_json(cleaned_text)
    if parsed is not None:
        return parsed, {"mode": "direct_json", "repaired": False}

    candidate = extract_json_object(cleaned_text)
    if candidate:
        parsed = try_parse_json(candidate)
        if parsed is not None:
            return parsed, {"mode": "extracted_json", "repaired": False}

    repaired = repair_json_via_model(
        host=host,
        timeout_sec=timeout_sec,
        model_name=model_name,
        raw_text=raw_text,
    )
    if repaired is not None:
        repaired["trajectory"] = list(repaired.get("trajectory", [])) + [
            {"step": 99, "action": "repair_parse", "detail": "Recovered JSON via repair prompt."}
        ]
        return repaired, {"mode": "repair_prompt", "repaired": True}

    return (
        {
            "summary": raw_text[:400],
            "commands": ["rg --files"],
            "files_touched": [],
            "file_writes": {},
            "patch_text": "--- a/README.md\n+++ b/README.md\n@@\n+Non-JSON fallback from Ollama agent\n",
            "trajectory": [
                {"step": 1, "action": "fallback_parse", "detail": "Model returned non-JSON output."}
            ],
        },
        {"mode": "fallback_parse", "repaired": False},
    )


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def try_parse_json(text: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return ""
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def repair_json_via_model(
    host: str,
    timeout_sec: int,
    model_name: str,
    raw_text: str,
) -> dict[str, object] | None:
    prompt = (
        "Convert the following agent output into valid JSON only.\n"
        "Return exactly one JSON object with these keys: "
        "summary, commands, files_touched, file_writes, patch_text, trajectory.\n"
        "Rules:\n"
        "- commands must be an array of strings\n"
        "- files_touched must be an array of strings\n"
        "- file_writes must be an object mapping relative file paths to full file contents\n"
        "- trajectory must be an array\n"
        "- if a value is missing, use an empty string, empty array, or empty object\n"
        "- do not add markdown fences or prose\n\n"
        "Agent output to normalize:\n"
        f"{raw_text[:12000]}"
    )
    body = post_generate(
        host=host,
        timeout_sec=timeout_sec,
        payload={
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_ctx": 4096,
                "num_predict": 700,
            },
        },
    )
    repaired_text = strip_code_fences(str(body.get("response", "")).strip())
    parsed = try_parse_json(repaired_text)
    if parsed is not None:
        return parsed
    candidate = extract_json_object(repaired_text)
    if candidate:
        return try_parse_json(candidate)
    return None


def coerce_file_writes(value: object) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    if isinstance(value, str):
        parsed = try_parse_json(value)
        if isinstance(parsed, dict):
            return {str(key): str(item) for key, item in parsed.items()}
        matches = re.findall(
            r'(?ms)"(?P<path>[^"\n]+)"\s*:\s*"(?P<content>(?:[^"\\]|\\.)*)"',
            value,
        )
        if matches:
            return {
                str(path): bytes(content, "utf-8").decode("unicode_escape")
                for path, content in matches
            }
        return {}
    if isinstance(value, list):
        coerced: dict[str, str] = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("file") or item.get("filename")
            content = item.get("content") or item.get("text") or item.get("value")
            if path is None or content is None:
                continue
            coerced[str(path)] = str(content)
        return coerced
    return {}


def finalize_file_writes(
    parsed: dict[str, object],
    files_touched: list[str],
    patch_text: str,
) -> dict[str, str]:
    file_writes = coerce_file_writes(parsed.get("file_writes", {}))
    if file_writes:
        return file_writes
    if len(files_touched) != 1:
        return {}
    candidate = patch_text.strip()
    if not candidate or looks_like_unified_diff(candidate):
        return {}
    return {files_touched[0]: candidate}


def looks_like_unified_diff(text: str) -> bool:
    markers = ("--- ", "+++ ", "@@")
    return any(marker in text for marker in markers)
