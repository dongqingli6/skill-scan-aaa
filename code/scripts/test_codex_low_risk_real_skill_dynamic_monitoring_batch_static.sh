#!/usr/bin/env bash
set -euo pipefail

# Stage 23 low-risk dynamic monitoring batch static/monkeypatch test.
# This test does not run real Docker, Codex, strace, uploaded scripts, real
# skills, network commands, or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path
from subprocess import CompletedProcess

runner_path = Path("code/scripts/run_codex_low_risk_real_skill_dynamic_monitoring_batch.py")
assert runner_path.exists(), "Stage 23 runner missing"
text = runner_path.read_text(encoding="utf-8")

assert "ALLOWED_CANDIDATE_ARCHIVES = (\"ideation.zip\", \"react-effect-patterns.zip\")" in text
assert "implementation-guide.zip" in text
assert "logging-best-practices.zip" in text
assert "val-town-cli.zip" in text
assert "docker pull" not in text.lower(), "image pull must not appear as a command"
assert "shell=True" not in text, "shell=True is forbidden"
assert "eval(" not in text, "eval is forbidden"
assert "codex exec" not in text.lower(), "Codex execution is forbidden"
assert "strace " not in text.lower(), "strace execution is forbidden"
assert "run_skill.sh" not in text.lower(), "uploaded run script execution is forbidden"
assert "install.sh" not in text.lower(), "uploaded install script execution is forbidden"
assert "setup.sh" not in text.lower(), "uploaded setup script execution is forbidden"

tree = ast.parse(text, filename=str(runner_path))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval is forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True is forbidden")

sys.path.insert(0, str(Path("code/scripts").resolve()))
spec = importlib.util.spec_from_file_location("stage23_runner", runner_path)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)

assert runner.ALLOWED_CANDIDATE_ARCHIVES == ("ideation.zip", "react-effect-patterns.zip")
stage20 = runner._load_stage20_by_archive()
for denied in ["implementation-guide.zip", "logging-best-practices.zip", "val-town-cli.zip"]:
    result = runner.validate_monitoring_candidate(denied, stage20.get(denied))
    assert result["allowed"] is False, (denied, result)
assert runner.validate_monitoring_candidate("ideation.zip", stage20["ideation.zip"])["allowed"] is True
assert runner.validate_monitoring_candidate("react-effect-patterns.zip", stage20["react-effect-patterns.zip"])["allowed"] is True

fake_high = dict(stage20["ideation.zip"])
fake_high["high"] = 1
assert runner.validate_monitoring_candidate("ideation.zip", fake_high)["allowed"] is False
fake_medium = dict(stage20["ideation.zip"])
fake_medium["medium"] = 1
assert runner.validate_monitoring_candidate("ideation.zip", fake_medium)["allowed"] is False
fake_critical = dict(stage20["ideation.zip"])
fake_critical["critical"] = 1
assert runner.validate_monitoring_candidate("ideation.zip", fake_critical)["allowed"] is False

cmd_info = runner.build_monitoring_command(
    "synthetic",
    Path("analysis_results/real_skill_intake/quarantine/ideation_28b8bbbee23c/uploaded_skill"),
    Path("analysis_results/real_skill_dynamic_monitoring_batch/static_test"),
)
command = cmd_info["command"]
assert command[:2] == ["docker", "run"], command
assert "--network" in command and command[command.index("--network") + 1] == "none", command
assert "--cap-drop" in command and command[command.index("--cap-drop") + 1] == "ALL", command
assert "--security-opt" in command and command[command.index("--security-opt") + 1] == "no-new-privileges", command
assert "--read-only" in command, command
assert "--pids-limit" in command, command
assert "--memory" in command, command
assert "--cpus" in command, command
assert "--privileged" not in command, command
assert not ("--network" in command and command[command.index("--network") + 1] == "host"), command
assert not any("/var/run/docker.sock" in item or "docker.sock" in item for item in command), command
assert not any(item == "pull" for item in command), command
assert "HOME=/home/codexsafe" in command, command
assert "CODEX_HOME=/home/codexsafe/.codex" in command, command
assert any(item.endswith(":/workspace/skill:ro") for item in command), command
assert any(item.endswith(":/output:rw") for item in command), command
assert cmd_info["docker_pull_executed"] is False
assert cmd_info["real_token_forbidden"] is True
assert cmd_info["uploaded_scripts_executed"] is False
assert cmd_info["codex_executed"] is False
assert cmd_info["strace_executed"] is False

calls = []
original_run = runner.stage21.subprocess.run

def fake_run(command, **kwargs):
    calls.append(command)
    assert kwargs.get("env", {}).get("HOME") == "/home/codexsafe"
    assert kwargs.get("env", {}).get("CODEX_HOME") == "/home/codexsafe/.codex"
    if command[:3] == ["docker", "image", "inspect"]:
        return CompletedProcess(command, 0, stdout="[]", stderr="")
    if command[:2] == ["docker", "run"]:
        return CompletedProcess(command, 0, stdout="benign monitoring", stderr="")
    raise AssertionError(f"unexpected subprocess command: {command}")

temp_root = Path(tempfile.mkdtemp(prefix="codex-stage23-static-"))
runner.stage21.subprocess.run = fake_run
try:
    runner.OUTPUT_ROOT = temp_root / "batch"
    runner.RUNS_DIR = runner.OUTPUT_ROOT / "runs"
    summary = runner.run_batch(
        Path("analysis_results/real_skill_intake/inbox"),
        ["ideation.zip", "react-effect-patterns.zip"],
        repeat=2,
        require_human_approved=True,
    )
finally:
    runner.stage21.subprocess.run = original_run

assert len([call for call in calls if call[:3] == ["docker", "image", "inspect"]]) == 4, calls
assert len([call for call in calls if call[:2] == ["docker", "run"]]) == 4, calls
assert summary["allowed_candidates"] == ["ideation.zip", "react-effect-patterns.zip"], summary
assert summary["blocked_archives_not_run"] == [
    "implementation-guide.zip",
    "logging-best-practices.zip",
    "val-town-cli.zip",
], summary
assert summary["docker_pull_executed"] is False, summary
assert summary["codex_executed"] is False, summary
assert summary["strace_executed"] is False, summary
assert summary["uploaded_scripts_executed"] is False, summary
assert summary["real_tokens_passed_to_container"] is False, summary
for archive_name in ["ideation.zip", "react-effect-patterns.zip"]:
    item = summary["per_sample"][archive_name]
    assert item["rounds_requested"] == 2, item
    assert item["rounds_completed"] == 2, item
    assert item["all_rounds_runtime_boundary_passed"] is True, item
    assert item["network_modes"] == ["none"], item

for path in ["summary.json", "report.md", "risk_table.csv", "repeatability_report.md"]:
    assert (runner.OUTPUT_ROOT / path).exists(), path

if temp_root.exists():
    shutil.rmtree(temp_root)

print("Codex low-risk real skill dynamic monitoring batch static test passed.")
PY

echo "Codex low-risk real skill dynamic monitoring batch static test passed."
