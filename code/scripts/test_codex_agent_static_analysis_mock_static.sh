#!/usr/bin/env bash
set -euo pipefail

# Stage 25A mock analyzer static test.
# This test uses provider=mock only. It does not run Docker, Codex, Claude
# Code, strace, real skills, network commands, uploaded scripts, or dependency
# installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

root = Path("code/platforms/codex/agent_static_analysis")
analyzer_path = root / "agent_static_analyzer.py"
runner_path = Path("code/scripts/run_codex_agent_static_analysis.py")
assert analyzer_path.exists(), "agent analyzer missing"
assert runner_path.exists(), "agent static CLI missing"
for path in [analyzer_path, runner_path]:
    text = path.read_text(encoding="utf-8")
    assert "subprocess" not in text, f"subprocess use forbidden in {path}"
    assert "docker run" not in text.lower(), f"Docker run forbidden in {path}"
    assert "codex exec" not in text.lower(), f"Codex execution forbidden in {path}"
    assert "claude code" not in text.lower(), f"Claude Code execution forbidden in {path}"
    assert "strace " not in text.lower(), f"strace execution forbidden in {path}"
    assert "run_skill.sh" not in text.lower(), f"skill execution forbidden in {path}"
    assert "os.environ" not in text, f"real environment access forbidden in {path}"
    assert "shell=True" not in text, f"shell=True forbidden in {path}"
    assert "eval(" not in text, f"eval forbidden in {path}"
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval forbidden in {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True forbidden in {path}")

sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("agent_static_analyzer", analyzer_path)
analyzer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(analyzer)
assert analyzer.DEFAULT_PROVIDER == "mock"

summary = json.loads(Path("analysis_results/real_skill_batch_static_dashboard/summary.json").read_text(encoding="utf-8"))
samples = {sample["archive_name"]: sample for sample in summary["samples"]}
high_report = analyzer.analyze_sample_static(samples["implementation-guide.zip"], provider="mock")
assert high_report["risk_summary"]["high"] >= 1, high_report
assert high_report["recommended_gate"] == "denied", high_report
clean_report = analyzer.analyze_sample_static(samples["ideation.zip"], provider="mock")
assert clean_report["recommended_gate"] == "allowed_for_manual_review", clean_report
disabled_report = analyzer.analyze_sample_static(samples["ideation.zip"], provider="codex")
assert disabled_report["agent_failed"] is True, disabled_report
assert disabled_report["recommended_gate"] == "manual_review", disabled_report

spec = importlib.util.spec_from_file_location("agent_static_cli", runner_path)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)
temp_root = Path(tempfile.mkdtemp(prefix="codex-stage25a-static-"))
try:
    runner.OUTPUT_ROOT = temp_root / "agent_static_analysis"
    runner.AGENT_REPORTS_DIR = runner.OUTPUT_ROOT / "agent_reports"
    runner.AGGREGATED_DIR = runner.OUTPUT_ROOT / "aggregated"
    cli_summary = runner.run_agent_static_analysis(
        "analysis_results/real_skill_batch_static_dashboard/summary.json",
        provider="mock",
    )
    assert cli_summary["provider"] == "mock", cli_summary
    assert cli_summary["provider_is_mock"] is True, cli_summary
    assert cli_summary["docker_executed"] is False, cli_summary
    assert cli_summary["codex_executed"] is False, cli_summary
    assert cli_summary["claude_code_executed"] is False, cli_summary
    assert cli_summary["strace_executed"] is False, cli_summary
    assert cli_summary["real_skill_executed"] is False, cli_summary
    for name in ["summary.json", "report.md", "risk_table.csv"]:
        assert (runner.OUTPUT_ROOT / name).exists(), name
finally:
    if temp_root.exists():
        shutil.rmtree(temp_root)

print("Codex agent static analysis mock static test passed.")
PY

echo "Codex agent static analysis mock static test passed."
