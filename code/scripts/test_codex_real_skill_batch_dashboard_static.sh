#!/usr/bin/env bash
set -euo pipefail

# Stage 20 real skill batch dashboard static test.
# This test reads generated dashboard artifacts only. It does not run Docker,
# Codex, strace, real skills, uploaded scripts, network commands, or installers.

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

root = Path("analysis_results/real_skill_batch_static_dashboard")
summary_path = root / "summary.json"
report_path = root / "report.md"
risk_table_path = root / "risk_table.csv"
recommendations_path = root / "recommendations.md"

for path in [summary_path, report_path, risk_table_path, recommendations_path]:
    assert path.exists(), f"missing dashboard artifact: {path}"
    assert path.is_file(), f"not a file: {path}"

summary = json.loads(summary_path.read_text(encoding="utf-8"))
assert summary["total_samples"] == 5, summary
assert summary["processed"] == 5, summary
assert summary["failed"] == 0, summary
assert summary["docker_executed"] is False, summary
assert summary["codex_executed"] is False, summary
assert summary["strace_executed"] is False, summary
assert summary["real_skills_executed"] is False, summary
assert summary["network_enabled"] is False, summary

by_name = {sample["archive_name"]: sample for sample in summary["samples"]}
assert by_name["implementation-guide.zip"]["category"] == "blocked", by_name["implementation-guide.zip"]
assert by_name["ideation.zip"]["category"] == "stage21_candidate", by_name["ideation.zip"]
assert by_name["react-effect-patterns.zip"]["category"] == "stage21_candidate", by_name["react-effect-patterns.zip"]
assert by_name["logging-best-practices.zip"]["category"] == "manual_review", by_name["logging-best-practices.zip"]
assert by_name["val-town-cli.zip"]["category"] == "manual_review", by_name["val-town-cli.zip"]

report = report_path.read_text(encoding="utf-8")
for required in [
    "Stage 20 Real Skill Batch Static Evaluation + Risk Dashboard",
    "implementation-guide.zip",
    "HIGH / CRITICAL static findings block dynamic execution",
    "docker_executed: `false`",
    "codex_executed: `false`",
    "strace_executed: `false`",
    "real_skills_executed: `false`",
]:
    assert required in report, required

csv_text = risk_table_path.read_text(encoding="utf-8")
assert "implementation-guide.zip,blocked" in csv_text, csv_text
assert "ideation.zip,stage21_candidate" in csv_text, csv_text
assert "react-effect-patterns.zip,stage21_candidate" in csv_text, csv_text
assert "logging-best-practices.zip,manual_review" in csv_text, csv_text
assert "val-town-cli.zip,manual_review" in csv_text, csv_text

print("Codex real skill batch dashboard static test passed.")
PY

echo "Codex real skill batch dashboard static test passed."
