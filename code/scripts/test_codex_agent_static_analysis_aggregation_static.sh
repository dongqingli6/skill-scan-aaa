#!/usr/bin/env bash
set -euo pipefail

# Stage 25A aggregation static test.
# This test does not run Docker, Codex, Claude Code, strace, real skills,
# network commands, uploaded scripts, or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

path = Path("code/platforms/codex/agent_static_analysis/agent_result_aggregator.py")
assert path.exists(), "agent result aggregator missing"
text = path.read_text(encoding="utf-8")
assert "shell=True" not in text
assert "eval(" not in text
tree = ast.parse(text, filename=str(path))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True forbidden")

spec = importlib.util.spec_from_file_location("agent_result_aggregator", path)
aggregator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(aggregator)

det_high = {"archive_name": "det-high.zip", "critical": 0, "high": 1, "medium": 0, "low": 0, "informational": 0}
agent_low = {"sample_name": "det-high.zip", "risk_summary": {"critical": 0, "high": 0, "medium": 0, "low": 1, "informational": 0}, "agent_failed": False}
result = aggregator.aggregate_agent_result(det_high, agent_low)
assert result["final_highest"] == "high", result
assert result["recommended_gate"] == "denied", result
assert result["agent_can_lower_risk"] is False, result

det_low = {"archive_name": "agent-high.zip", "critical": 0, "high": 0, "medium": 0, "low": 1, "informational": 0}
agent_high = {"sample_name": "agent-high.zip", "risk_summary": {"critical": 0, "high": 1, "medium": 0, "low": 0, "informational": 0}, "agent_failed": False}
result = aggregator.aggregate_agent_result(det_low, agent_high)
assert result["final_highest"] == "high", result
assert result["recommended_gate"] == "denied", result

det_clean = {"archive_name": "clean.zip", "critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
agent_failed = {"sample_name": "clean.zip", "risk_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}, "agent_failed": True}
result = aggregator.aggregate_agent_result(det_clean, agent_failed)
assert result["recommended_gate"] == "manual_review", result
assert result["can_execute_dynamically"] is False, result
assert "agent-assisted static analysis failed" in " ".join(result["blockers"]), result

print("Codex agent static analysis aggregation static test passed.")
PY

echo "Codex agent static analysis aggregation static test passed."
