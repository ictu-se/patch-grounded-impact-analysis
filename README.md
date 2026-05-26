# Patch-Grounded Software Change Impact Analysis

This repository contains the experiment harness, benchmark scaffold assets, analysis scripts, and reproducibility instructions for the study "Patch-Grounded Software Change Impact Analysis and Regression Test Triage with Large Language Models."

The study evaluates how process and context scaffolds affect coding-agent behavior on small software repair tasks. This GitHub repository contains only the code and minimal instructions needed to rerun the experiments. Dataset files, generated run artifacts, manuscript files, and writing notes are not uploaded here.

Public repository: https://github.com/ictu-se/patch-grounded-impact-analysis

## Repository Layout

- `benchmark/`: scaffold assets plus instructions for downloading the benchmark task bundle.
- `harness/`: experiment runner, condition injection, model adapters, evaluation, telemetry, and workspace management.
- `analysis/`: scripts for rebuilding summaries, robustness checks, bootstrap intervals, and figures.
- `analysis/outputs/`: derived outputs restored from the external artifact archive or rebuilt locally.
- `runs/metrics/`: per-trial metric records restored from the external artifact archive or regenerated locally.
- `runs/patches/`: generated patch artifacts restored from the external artifact archive or regenerated locally.
- `runs/trajectories/`: saved trajectories restored from the external artifact archive or regenerated locally.
- `docs/DATASETS.md`: external dataset and artifact links.

The repository intentionally ignores `benchmark/repos/`, `benchmark/tasks.json`, `analysis/outputs/`, and `runs/`. Those are dataset or generated artifact folders, so they should be downloaded from the external archive or regenerated rather than uploaded directly to GitHub.

The seed benchmark repositories intentionally contain failing implementations. Run them through the harness or target a specific repaired workspace; a root-level `pytest` run is not the validity check for this repository.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer for JavaScript benchmark tasks
- Ollama for local LLM runs
- Python packages listed in `requirements.txt`

Install the Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Install the primary Ollama models:

```powershell
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b
```

## Quick Reproduction

Start Ollama:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_ollama.ps1
```

Run the compact factorial core:

```powershell
python run_pilot.py --conditions harness/configs/conditions_factorial_retries_4.json --model qwen2.5-coder:7b
```

Run the challenge surface:

```powershell
python run_pilot.py --conditions harness/configs/conditions_challenge_surface_retries_2.json --model qwen2.5-coder:7b
```

Run the model-scale replication:

```powershell
python run_model_comparison.py --conditions harness/configs/conditions_factorial_retries_4.json --model qwen2.5-coder:14b
```

## Rebuild Analysis Outputs

```powershell
python analysis/rebuild_summary.py
python analysis/build_surface_tables.py
python analysis/build_replication_slice.py
python analysis/surface_robustness_checks.py
python analysis/bootstrap_uncertainty.py
```

The main derived files are written to `analysis/outputs/`. That directory is ignored by Git because it is generated output, not source code.

## GitHub Preparation

The `.gitignore` file keeps datasets, generated outputs, runtime checkpoints, logs, manuscript files, LaTeX build products, PDFs, and ZIP bundles out of version control.

Public GitHub URL: https://github.com/ictu-se/patch-grounded-impact-analysis
