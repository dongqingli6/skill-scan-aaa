#!/usr/bin/env bash
set -euo pipefail

# Big Stage 25 controlled activation command-builder static test.
# This test builds command arrays only. It does not run Docker, Codex, Claude
# Code, strace, real skills, network commands, uploaded scripts, or installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

root = Path("code/platforms/codex/controlled_activation")
runner_path = root / "activation_runner.py"
assert runner_path.exists(), "activation_runner.py missing"
text = runner_path.read_text(encoding="utf-8")
assert "shell=True" not in text
assert "eval(" not in text
assert "codex exec" not in text.lower()
assert "claude code" not in text.lower()
assert "strace " not in text.lower()
assert "run_skill.sh" not in text.lower()
tree = ast.parse(text, filename=str(runner_path))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True forbidden")

sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("activation_runner", runner_path)
activation_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(activation_runner)
cmd_info = activation_runner.build_activation_docker_command(
    "synthetic",
    Path("analysis_results/real_skill_intake/quarantine/ideation_28b8bbbee23c/uploaded_skill"),
    Path("analysis_results/controlled_skill_activation/test_output"),
    "metadata",
)
command = cmd_info["command"]
assert command[:2] == ["docker", "run"], command
assert "--network" in command and command[command.index("--network") + 1] == "none", command
assert "--cap-drop" in command and command[command.index("--cap-drop") + 1] == "ALL", command
assert "--security-opt" in command and command[command.index("--security-opt") + 1] == "no-new-privileges", command
assert "--read-only" in command, command
assert "--tmpfs" in command and "/tmp:rw,noexec,nosuid,nodev" in command, command
assert "--tmpfs" in command and "/run:rw,noexec,nosuid,nodev" in command, command
assert "--pids-limit" in command and command[command.index("--pids-limit") + 1] == "128", command
assert "--memory" in command and command[command.index("--memory") + 1] == "256m", command
assert "--cpus" in command and command[command.index("--cpus") + 1] == "1.0", command
assert "--privileged" not in command, command
assert not ("--network" in command and command[command.index("--network") + 1] == "host"), command
assert not any("/var/run/docker.sock" in item or "docker.sock" in item for item in command), command
assert not any(item == "pull" for item in command), command
assert "HOME=/home/codexsafe" in command, command
assert "CODEX_HOME=/home/codexsafe/.codex" in command, command
assert any(item.endswith(":/workspace/skill:ro") for item in command), command
assert any(item.endswith(":/output:rw") for item in command), command
assert cmd_info["docker_pull_executed"] is False
assert cmd_info["codex_executed"] is False
assert cmd_info["claude_code_executed"] is False
assert cmd_info["strace_executed"] is False
assert cmd_info["uploaded_scripts_executed"] is False
assert activation_runner.inspect_local_image_command() == ["docker", "image", "inspect", "python:3.11-slim"]
assert activation_runner.sanitized_subprocess_env()["HOME"] == "/home/codexsafe"
assert activation_runner.sanitized_subprocess_env()["CODEX_HOME"] == "/home/codexsafe/.codex"

print("Codex controlled activation command static test passed.")
PY

echo "Codex controlled activation command static test passed."
