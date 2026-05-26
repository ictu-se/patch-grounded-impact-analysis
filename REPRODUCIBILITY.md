# Reproducibility Notes

This package supports the software-engineering scaffold study.

## Environment

- Operating system: Microsoft Windows 11 Home Single Language, x64, version 10.0.26200
- CPU: Intel Core Ultra 9 275HX, 24 cores / 24 logical processors
- Memory: 32 GB RAM
- GPU available on the host: NVIDIA GeForce RTX 5080 Laptop GPU
- Agent backend: Ollama
- Primary model: qwen2.5-coder:7b
- Replication model: qwen2.5-coder:14b

## Key Folders

- `benchmark/`: repair tasks, guidance templates, and skills
- `harness/`: experiment runner and condition configs
- `analysis/`: scripts used to rebuild summaries and figures
- `analysis/outputs/`: derived CSV/JSON/Markdown outputs restored from the external artifact archive or rebuilt locally
- `runs/metrics/`: per-trial metric records restored from the external artifact archive or regenerated locally
- `runs/patches/`: patch artifacts restored from the external artifact archive or regenerated locally
- `runs/trajectories/`: saved trajectory records restored from the external artifact archive or regenerated locally
- `docs/DATASETS.md`: external dataset and artifact links

The folders `benchmark/repos/`, `benchmark/tasks.json`, `analysis/outputs/`, and `runs/` are not tracked in Git. The download links for these dataset and artifact folders should be recorded in `docs/DATASETS.md` after the public archive is created.

Manuscript files, LaTeX sources, PDFs, and writing notes are intentionally excluded from the public code repository. A user who wants to reproduce the experiments should clone this repository, download the external dataset bundle, install dependencies, and run the commands below.

## Setup

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Install the local models:

```powershell
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b
```

## Representative Commands

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

Rebuild analysis outputs:

```powershell
python analysis/rebuild_summary.py
python analysis/build_surface_tables.py
python analysis/bootstrap_uncertainty.py
```

## Repository Status

Public code repository: https://github.com/ictu-se/patch-grounded-impact-analysis
