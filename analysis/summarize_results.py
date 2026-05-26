from __future__ import annotations

import csv
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    summary_path = root / "runs" / "metrics" / "summary_partial.csv"
    if not summary_path.exists():
        print("No summary file found.")
        return 1

    rows = list(csv.DictReader(summary_path.open(encoding="utf-8")))
    print(f"rows={len(rows)}")
    passed = sum(1 for row in rows if row["evaluation_passed"] == "True")
    print(f"passed={passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
