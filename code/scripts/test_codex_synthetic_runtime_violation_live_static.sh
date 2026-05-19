#!/usr/bin/env bash
set -euo pipefail

# Stage 24 synthetic live static test.
# This test uses synthetic events and a fake kill callback only. It does not
# run Docker, Codex, strace, real skills, network commands, uploaded scripts,
# or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

runner_path = Path("code/scripts/run_codex_synthetic_runtime_violation_live_test.py")
assert runner_path.exists(), "synthetic runtime violation runner missing"
text = runner_path.read_text(encoding="utf-8")
assert "--synthetic" in text, "--synthetic support missing"
assert "--dry-run-kill" in text, "--dry-run-kill support missing"
assert "docker kill" not in text.lower(), "real docker kill must not appear"
assert "subprocess" not in text, "runner must not execute subprocesses"
assert "codex exec" not in text.lower(), "Codex execution is forbidden"
assert "strace " not in text.lower(), "strace execution is forbidden"
assert "run_skill.sh" not in text.lower(), "real skill execution is forbidden"
assert "shell=True" not in text, "shell=True is forbidden"
assert "eval(" not in text, "eval is forbidden"

tree = ast.parse(text, filename=str(runner_path))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval is forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True is forbidden")

sys.path.insert(0, str(Path("code/platforms/codex/enforcer/runtime_violation").resolve()))
spec = importlib.util.spec_from_file_location("stage24_runner", runner_path)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)

temp_root = Path(tempfile.mkdtemp(prefix="codex-stage24-static-"))
runner.runtime_violation_report.OUTPUT_ROOT = temp_root / "runtime_violation_synthetic_live"
try:
    summary = runner.run_synthetic_runtime_violation_live_test(synthetic=True, dry_run_kill=True)
    output_root = runner.runtime_violation_report.OUTPUT_ROOT
    for name in ["summary.json", "violation_event.json", "violation_report.json", "report.md", "risk_table.csv"]:
        assert (output_root / name).exists(), name
    saved_summary = json.loads((output_root / "summary.json").read_text(encoding="utf-8"))
    assert saved_summary["real_container_killed"] is False, saved_summary
    assert saved_summary["fake_kill_callback_called"] is True, saved_summary
    assert saved_summary["docker_executed"] is False, saved_summary
    assert saved_summary["codex_executed"] is False, saved_summary
    assert saved_summary["strace_executed"] is False, saved_summary
    assert saved_summary["real_skill_executed"] is False, saved_summary
    assert saved_summary["network_enabled"] is False, saved_summary
    assert saved_summary["final_status"] == "pass", saved_summary
    assert summary == saved_summary, (summary, saved_summary)
finally:
    if temp_root.exists():
        shutil.rmtree(temp_root)

print("Codex synthetic runtime violation live static test passed.")
PY

echo "Codex synthetic runtime violation live static test passed."
