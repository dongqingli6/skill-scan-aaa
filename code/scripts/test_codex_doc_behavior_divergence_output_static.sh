#!/usr/bin/env bash
set -euo pipefail

# Big Stage 26 output static test.
# This test performs document/evidence analysis only. It does not run Docker,
# Codex, Claude Code, strace, real skills, network commands, uploaded scripts,
# installers, or real APIs.

python3 code/scripts/run_codex_doc_behavior_divergence_analysis.py \
  --inbox analysis_results/real_skill_intake/inbox \
  --include-all-real-skills >/tmp/codex_doc_behavior_divergence_output_static.json

python3 - <<'PY'
from __future__ import annotations

import csv
import json
from pathlib import Path

root = Path("analysis_results/doc_behavior_divergence")
required = [
    "summary.json",
    "report.md",
    "risk_table.csv",
    "divergence_matrix.json",
    "manual_review_queue.md",
]
for name in required:
    assert (root / name).exists(), f"{name} missing"

summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
assert summary["stage"] == "Big Stage 26 Document-Behavior Divergence Analysis Layer"
assert summary["total_samples"] == 5
assert summary["docker_executed"] is False
assert summary["codex_executed"] is False
assert summary["claude_code_executed"] is False
assert summary["strace_executed"] is False
assert summary["real_skill_executed"] is False
assert summary["real_api_called"] is False
assert summary["network_enabled"] is False

matrix = json.loads((root / "divergence_matrix.json").read_text(encoding="utf-8"))
for sample in [
    "implementation-guide.zip",
    "logging-best-practices.zip",
    "val-town-cli.zip",
    "ideation.zip",
    "react-effect-patterns.zip",
]:
    assert sample in matrix, sample

report = (root / "report.md").read_text(encoding="utf-8")
for sample in matrix:
    assert sample in report
assert "Claims:" in report
assert "Evidence:" in report
assert "Divergence:" in report
assert "Final recommendation:" in report

queue = (root / "manual_review_queue.md").read_text(encoding="utf-8")
assert "Stage 26 Manual Review Queue" in queue
assert any(item["decision"] in ("blocked", "manual_review") for item in summary["results"])

rows = list(csv.DictReader((root / "risk_table.csv").open(encoding="utf-8")))
assert len(rows) == 5
assert {"archive_name", "divergence_highest", "final_risk", "decision", "review_queue"}.issubset(rows[0])

print("Codex doc-behavior divergence output static test passed.")
PY

echo "Codex doc-behavior divergence output static test passed."
