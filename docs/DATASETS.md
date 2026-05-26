# Dataset Sources

This repository does not upload raw datasets or generated run artifacts. The GitHub repository is intended to contain code, scaffold definitions, paper source, and reproducibility instructions only.

## Required External Artifacts

Add the final public links here before release:

| Artifact | Contents | Public link |
| --- | --- | --- |
| Benchmark task bundle | Seed repositories and `benchmark/tasks.json` | TODO: add Zenodo/OSF/GitHub Release URL |
| Trial metrics | Per-trial metric JSON files and `summary_partial.csv` | TODO: add Zenodo/OSF/GitHub Release URL |
| Patch artifacts | Generated patches for completed trials | TODO: add Zenodo/OSF/GitHub Release URL |
| Trajectories | Saved trial trajectory JSON files | TODO: add Zenodo/OSF/GitHub Release URL |
| Derived analysis outputs | CSV, JSON, and Markdown outputs under `analysis/outputs/` | TODO: add Zenodo/OSF/GitHub Release URL |

## Expected Local Layout

After downloading the artifact bundle, place files in this layout:

```text
benchmark/
  repos/
  tasks.json
analysis/
  outputs/
runs/
  metrics/
  patches/
  trajectories/
```

The code can be uploaded before these links are assigned, but the camera-ready paper should not claim a public dataset URL until the archive exists.
