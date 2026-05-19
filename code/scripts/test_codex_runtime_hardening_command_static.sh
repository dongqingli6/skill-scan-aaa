#!/usr/bin/env bash
set -euo pipefail

# Stage 22 command hardening static/monkeypatch test.
# This test builds command arrays only. It does not run real Docker, Codex,
# strace, real skills, uploaded scripts, network commands, or installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

files = [
    Path("web_ui/safe_dynamic_runner.py"),
    Path("code/scripts/run_codex_real_skill_controlled_dynamic_inspection.py"),
]

for path in files:
    assert path.exists(), f"missing command builder: {path}"
    text = path.read_text(encoding="utf-8")
    assert "docker pull" not in text.lower(), f"docker pull must not appear in {path}"
    assert "shell=True" not in text, f"shell=True is forbidden in {path}"
    assert "eval(" not in text, f"eval is forbidden in {path}"
    assert "codex exec" not in text.lower(), f"Codex execution is forbidden in {path}"
    assert "strace " not in text.lower(), f"strace execution is forbidden in {path}"
    assert "os.environ.copy" not in text, f"host environment copy is forbidden in {path}"
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval call forbidden in {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True forbidden in {path}")

spec = importlib.util.spec_from_file_location("safe_dynamic_runner", files[0])
sys.path.insert(0, str(Path("web_ui").resolve()))
safe_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(safe_runner)

web_cmd_info = safe_runner.build_safe_dynamic_command(
    {"job_id": "synthetic", "extracted_skill_path": "analysis_results/real_skill_intake/quarantine/ideation_28b8bbbee23c/uploaded_skill"},
    Path("analysis_results/runtime_hardening_command_static/web"),
)

spec = importlib.util.spec_from_file_location("stage21_runner", files[1])
stage21_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(stage21_runner)

stage21_cmd_info = stage21_runner.build_benign_inspection_command(
    "synthetic",
    Path("analysis_results/real_skill_intake/quarantine/ideation_28b8bbbee23c/uploaded_skill"),
    Path("analysis_results/runtime_hardening_command_static/stage21"),
)

for cmd_info in [web_cmd_info, stage21_cmd_info]:
    command = cmd_info["command"]
    assert command[:2] == ["docker", "run"], command
    assert "--network" in command and command[command.index("--network") + 1] == "none", command
    assert "--read-only" in command, command
    assert "--cap-drop" in command and command[command.index("--cap-drop") + 1] == "ALL", command
    assert "--security-opt" in command and command[command.index("--security-opt") + 1] == "no-new-privileges", command
    assert "--pids-limit" in command, command
    assert "--memory" in command, command
    assert "--cpus" in command, command
    assert "--privileged" not in command, command
    assert not ("--network" in command and command[command.index("--network") + 1] == "host"), command
    assert not any("/var/run/docker.sock" in item or "docker.sock" in item for item in command), command
    assert any(item.endswith(":/workspace/skill:ro") for item in command), command
    assert any(item.endswith(":/output:rw") for item in command), command
    assert "HOME=/home/codexsafe" in command, command
    assert "CODEX_HOME=/home/codexsafe/.codex" in command, command
    assert cmd_info["hardening_policy_version"] == "stage22-runtime-hardening-v1", cmd_info
    assert cmd_info["no_new_privileges"] is True, cmd_info
    assert cmd_info["cap_drop_all"] is True, cmd_info
    assert cmd_info["read_only_rootfs"] is True, cmd_info
    assert cmd_info["docker_network_none"] is True, cmd_info
    assert cmd_info["docker_network_host_forbidden"] is True, cmd_info
    assert cmd_info["docker_sock_forbidden"] is True, cmd_info
    assert cmd_info["privileged_forbidden"] is True, cmd_info
    assert cmd_info["real_home_forbidden"] is True, cmd_info
    assert cmd_info["real_codex_home_forbidden"] is True, cmd_info
    assert cmd_info["real_token_forbidden"] is True, cmd_info
    assert cmd_info["uploaded_script_execution_forbidden"] is True, cmd_info
    assert cmd_info["install_command_forbidden"] is True, cmd_info
    assert cmd_info["docker_pull_forbidden"] is True, cmd_info
    assert cmd_info["local_image_preflight_required"] is True, cmd_info
    assert cmd_info["sanitized_env_required"] is True, cmd_info
    assert cmd_info["runtime_audit_complete"] is True, cmd_info
    assert cmd_info["uploaded_scripts_executed"] is False, cmd_info
    assert cmd_info["codex_executed"] is False, cmd_info
    assert cmd_info["strace_executed"] is False, cmd_info

assert "[\"docker\", \"image\", \"inspect\", image]" in files[0].read_text(encoding="utf-8")
assert "[\"docker\", \"image\", \"inspect\", image]" in files[1].read_text(encoding="utf-8")

print("Codex runtime hardening command static test passed.")
PY

echo "Codex runtime hardening command static test passed."
