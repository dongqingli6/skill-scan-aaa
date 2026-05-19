#!/usr/bin/env bash
set -euo pipefail

# Big Stage 27 runner static test.
# This test does not run Docker, Codex, Claude Code, strace, skills, network
# commands, installers, or real APIs.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

runner = Path("code/platforms/codex/scaled_validation/scaled_evaluation_runner.py")
cli = Path("code/scripts/run_codex_scaled_validation_report.py")
assert runner.exists(), "scaled_evaluation_runner.py missing"
assert cli.exists(), "CLI missing"

for path in [runner, cli, Path("code/platforms/codex/scaled_validation/report_builder.py"), Path("code/platforms/codex/scaled_validation/dashboard_data.py")]:
    text = path.read_text(encoding="utf-8")
    assert "subprocess" not in text, path
    assert "shell=True" not in text, path
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval forbidden in {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True forbidden in {path}")

cli_text = cli.read_text(encoding="utf-8")
assert "--static-only" in cli_text
assert "static-only mode only" in cli_text

sys.path.insert(0, str(Path("code/platforms/codex/scaled_validation").resolve()))
spec_builder = importlib.util.spec_from_file_location("synthetic_corpus_builder", Path("code/platforms/codex/scaled_validation/synthetic_corpus_builder.py"))
builder = importlib.util.module_from_spec(spec_builder)
assert spec_builder.loader is not None
spec_builder.loader.exec_module(builder)
builder.build_synthetic_corpus(Path("analysis_results/scaled_validation/synthetic_corpus"))

spec_runner = importlib.util.spec_from_file_location("scaled_evaluation_runner", runner)
module = importlib.util.module_from_spec(spec_runner)
assert spec_runner.loader is not None
spec_runner.loader.exec_module(module)
summary = module.run_scaled_evaluation(Path(".").resolve(), include_real_skills=True)
assert summary["docker_executed"] is False
assert summary["codex_executed"] is False
assert summary["claude_code_executed"] is False
assert summary["strace_executed"] is False
assert summary["real_skill_executed"] is False
assert summary["real_api_called"] is False
assert summary["network_enabled"] is False
assert summary["synthetic_count"] >= 12
assert summary["real_skill_count"] == 5

print("Codex scaled validation runner static test passed.")
PY

echo "Codex scaled validation runner static test passed."
