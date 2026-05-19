#!/usr/bin/env bash
set -euo pipefail

# Big Stage 27 report static test.

python3 code/scripts/run_codex_scaled_validation_report.py \
  --build-synthetic-corpus \
  --include-real-skills \
  --static-only >/tmp/codex_scaled_validation_report_static.json

python3 - <<'PY'
from __future__ import annotations

import csv
import json
from pathlib import Path

assert Path("code/platforms/codex/scaled_validation/report_builder.py").exists()
root = Path("analysis_results/scaled_validation")
required = [
    "summary.json",
    "report.md",
    "risk_table.csv",
    "metrics.json",
    "confusion_matrix.json",
    "manual_review_queue.md",
    "final_research_report.md",
    "dashboard_data.json",
]
for name in required:
    assert (root / name).exists(), f"{name} missing"

report = (root / "final_research_report.md").read_text(encoding="utf-8")
for heading in ["Executive Summary", "Dataset", "Metrics", "Limitations", "Manual Review Queue"]:
    assert heading in report, heading

summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
assert summary["total_samples"] >= 17
assert summary["real_skill_count"] == 5
assert summary["synthetic_count"] >= 12
assert summary["docker_executed"] is False
assert summary["codex_executed"] is False
assert summary["claude_code_executed"] is False
assert summary["strace_executed"] is False
assert summary["real_skill_executed"] is False
assert summary["real_api_called"] is False
assert summary["network_enabled"] is False

rows = list(csv.DictReader((root / "risk_table.csv").open(encoding="utf-8")))
assert len(rows) >= 17
dashboard = json.loads((root / "dashboard_data.json").read_text(encoding="utf-8"))
assert "cards" in dashboard
assert "sample_table" in dashboard
assert "artifact_paths" in dashboard

print("Codex scaled validation report static test passed.")
PY

echo "Codex scaled validation report static test passed."
