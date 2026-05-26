from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.telemetry import SUMMARY_FIELDS


def main() -> int:
    root = ROOT
    metrics_dir = root / "runs" / "metrics"
    summary_path = metrics_dir / "summary_partial.csv"

    metric_files = sorted(path for path in metrics_dir.glob("*.json") if path.name != "summary_partial.csv")
    rows = []
    for path in metric_files:
        rows.append(json.loads(path.read_text(encoding="utf-8")))

    lines = [",".join(SUMMARY_FIELDS)]
    for row in rows:
        lines.append(",".join(str(row.get(field, "")) for field in SUMMARY_FIELDS))
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rebuilt_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
