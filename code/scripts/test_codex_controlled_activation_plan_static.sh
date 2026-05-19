#!/usr/bin/env bash
set -euo pipefail

# Big Stage 25 controlled activation plan-only static test.
# This test generates plans only. It does not run Docker, Codex, Claude Code,
# strace, real skills, network commands, uploaded scripts, or installers.

python3 - <<'PY'
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

runner_path = Path("code/scripts/run_codex_controlled_skill_activation.py")
assert runner_path.exists(), "controlled activation CLI missing"
text = runner_path.read_text(encoding="utf-8")
assert "--plan-only" in text
assert "--require-human-approved" in text
assert "subprocess" not in text
assert "codex exec" not in text.lower()
assert "claude code" not in text.lower()
assert "strace " not in text.lower()
assert "run_skill.sh" not in text.lower()
assert "shell=True" not in text

root = Path("code/platforms/codex/controlled_activation")
sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("activation_runner", root / "activation_runner.py")
activation_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(activation_runner)

temp_root = Path(tempfile.mkdtemp(prefix="codex-stage25-plan-"))
try:
    activation_runner.activation_plan.OUTPUT_ROOT = temp_root / "controlled_skill_activation"
    activation_runner.activation_plan.PLANS_DIR = activation_runner.activation_plan.OUTPUT_ROOT / "plans"
    activation_runner.activation_report.OUTPUT_ROOT = temp_root / "controlled_skill_activation"
    summary = activation_runner.run_controlled_activation_plan(
        inbox=Path("analysis_results/real_skill_intake/inbox"),
        sample_names=["ideation.zip", "react-effect-patterns.zip"],
        plan_only=True,
        require_human_approved=False,
    )
    assert summary["plan_only"] is True, summary
    assert summary["docker_executed"] is False, summary
    assert summary["codex_executed"] is False, summary
    assert summary["claude_code_executed"] is False, summary
    assert summary["strace_executed"] is False, summary
    assert summary["real_skill_executed"] is False, summary
    assert summary["network_enabled"] is False, summary
    for plan in summary["plans"]:
        assert plan["requires_human_confirmation"] is True, plan
        assert plan["final_activation_decision"] != "allowed", plan
    for sample in ["ideation_zip", "react-effect-patterns_zip"]:
        assert (activation_runner.activation_plan.PLANS_DIR / f"{sample}_activation_plan.json").exists(), sample
        assert (activation_runner.activation_plan.PLANS_DIR / f"{sample}_activation_plan.md").exists(), sample
    for name in ["summary.json", "report.md", "risk_table.csv", "activation_events.json", "runtime_audit.json"]:
        assert (activation_runner.activation_report.OUTPUT_ROOT / name).exists(), name
finally:
    if temp_root.exists():
        shutil.rmtree(temp_root)

print("Codex controlled activation plan static test passed.")
PY

echo "Codex controlled activation plan static test passed."
