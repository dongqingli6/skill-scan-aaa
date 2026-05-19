#!/usr/bin/env bash
set -euo pipefail

# Stage 28 multi-session policy static test.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

root = Path("code/platforms/codex/multi_session")
for name in ["session_runner.py", "session_policy.py", "session_report.py"]:
    path = root / name
    assert path.exists(), f"{name} missing"
    text = path.read_text(encoding="utf-8")
    assert "subprocess" not in text
    assert "shell=True" not in text
    assert "codex exec" not in text.lower()
    assert "claude" not in text.lower()
    assert "strace" not in text.lower()
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval forbidden in {path}")

sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("session_runner", root / "session_runner.py")
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)
events = runner.run_controlled_sessions("synthetic", 4, Path("analysis_results/controlled_sinkhole_dynamic/fake_home"))
assert len(events) == 4
assert events[0]["fake_home_reused"] is False
assert events[1]["fake_home_reused"] is True
assert all(event["skill_executed"] is False for event in events)
assert all(event["allowed"] is True for event in events)

print("Codex Stage 28 multi-session policy static test passed.")
PY

echo "Codex Stage 28 multi-session policy static test passed."
