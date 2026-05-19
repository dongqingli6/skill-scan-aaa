#!/usr/bin/env bash
set -euo pipefail

# Stage 21 controlled dynamic inspection static/monkeypatch test.
# This test does not run real Docker, Codex, strace, uploaded scripts, real
# skills, network commands, or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from subprocess import CompletedProcess

runner_path = Path("code/scripts/run_codex_real_skill_controlled_dynamic_inspection.py")
assert runner_path.exists(), "Stage 21 runner missing"
text = runner_path.read_text(encoding="utf-8")

assert "ALLOWED_CANDIDATE_ARCHIVES = (\"ideation.zip\", \"react-effect-patterns.zip\")" in text
assert "implementation-guide.zip" in text
assert "logging-best-practices.zip" in text
assert "val-town-cli.zip" in text
assert "docker pull" not in text.lower(), "docker pull must not appear"
assert "shell=True" not in text, "shell=True is forbidden"
assert "eval(" not in text, "eval is forbidden"
assert "codex exec" not in text.lower(), "Codex execution is forbidden"
assert "strace " not in text.lower(), "strace execution is forbidden"
assert "run_skill.sh" not in text.lower(), "uploaded run script execution is forbidden"
assert "install.sh" not in text.lower(), "uploaded install script execution is forbidden"
assert "setup.sh" not in text.lower(), "uploaded setup script execution is forbidden"
assert "os.environ.copy" not in text, "host environment copy is forbidden"
assert "sanitized_subprocess_env" in text, "sanitized env helper missing"
assert "[\"docker\", \"image\", \"inspect\", image]" in text, "image inspect preflight missing"

summary_path = Path("analysis_results/real_skill_controlled_dynamic_inspection/summary.json")
if summary_path.exists():
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
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
    by_name = {item["archive_name"]: item for item in summary["results"]}
    for archive_name in ["ideation.zip", "react-effect-patterns.zip"]:
        item = by_name[archive_name]
        assert item["container_started"] is True, item
        assert item["container_removed"] is True, item
        assert item["network_mode"] == "none", item
        assert item["runtime_image"] == "python:3.11-slim", item
        assert item["image_allowlisted"] is True, item
        assert item["image_present_locally"] is True, item
        assert item["docker_pull_executed"] is False, item
        assert item["sample_mount_mode"] == "read-only", item
        assert item["output_mount_mode"] == "writable", item
        assert item["fake_home_used"] is True, item
        assert item["fake_codex_home_used"] is True, item
        assert item["docker_sock_mounted"] is False, item
        assert item["privileged"] is False, item
        assert item["network_host"] is False, item
        assert item["real_tokens_passed_to_container"] is False, item
        assert item["uploaded_scripts_executed"] is False, item
        assert item["codex_executed"] is False, item
        assert item["strace_executed"] is False, item
        assert item["final_verdict"] == "controlled no-network benign inspection completed", item

tree = ast.parse(text, filename=str(runner_path))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval is forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True is forbidden")

spec = importlib.util.spec_from_file_location("stage21_runner", runner_path)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)

assert runner.ALLOWED_CANDIDATE_ARCHIVES == ("ideation.zip", "react-effect-patterns.zip")
stage20 = runner._stage20_by_archive()
for denied in ["implementation-guide.zip", "logging-best-practices.zip", "val-town-cli.zip"]:
    result = runner.validate_candidate_archive(denied, stage20.get(denied))
    assert result["allowed"] is False, (denied, result)
assert runner.validate_candidate_archive("ideation.zip", stage20["ideation.zip"])["allowed"] is True
assert runner.validate_candidate_archive("react-effect-patterns.zip", stage20["react-effect-patterns.zip"])["allowed"] is True

fake_high = dict(stage20["ideation.zip"])
fake_high["high"] = 1
assert runner.validate_candidate_archive("ideation.zip", fake_high)["allowed"] is False
fake_medium = dict(stage20["ideation.zip"])
fake_medium["medium"] = 1
assert runner.validate_candidate_archive("ideation.zip", fake_medium)["allowed"] is False

cmd_info = runner.build_benign_inspection_command(
    "synthetic",
    Path("analysis_results/real_skill_intake/quarantine/ideation_28b8bbbee23c/uploaded_skill"),
    Path("analysis_results/real_skill_controlled_dynamic_inspection/test_output"),
)
command = cmd_info["command"]
assert command[:2] == ["docker", "run"], command
assert "--network" in command and "none" in command, command
assert "--read-only" in command, command
assert "--cap-drop" in command and "ALL" in command, command
assert "--security-opt" in command and "no-new-privileges" in command, command
assert "--pids-limit" in command, command
assert "--memory" in command, command
assert "--cpus" in command, command
assert "--privileged" not in command, command
assert "host" not in command[command.index("--network") + 1], command
assert not any("/var/run/docker.sock" in item or "docker.sock" in item for item in command), command
assert any(item.endswith(":/workspace/skill:ro") for item in command), command
assert any(item.endswith(":/output:rw") for item in command), command
assert "HOME=/home/codexsafe" in command, command
assert "CODEX_HOME=/home/codexsafe/.codex" in command, command
assert cmd_info["uploaded_scripts_executed"] is False
assert cmd_info["codex_executed"] is False
assert cmd_info["strace_executed"] is False
assert cmd_info["hardening_policy_version"] == "stage22-runtime-hardening-v1"
assert cmd_info["no_new_privileges"] is True
assert cmd_info["cap_drop_all"] is True
assert cmd_info["read_only_rootfs"] is True
assert cmd_info["docker_network_none"] is True
assert cmd_info["docker_pull_forbidden"] is True
assert cmd_info["runtime_audit_complete"] is True

calls = []
original_run = runner.subprocess.run

def fake_run(command, **kwargs):
    calls.append(command)
    assert kwargs.get("env", {}).get("HOME") == "/home/codexsafe"
    assert kwargs.get("env", {}).get("CODEX_HOME") == "/home/codexsafe/.codex"
    if command[:3] == ["docker", "image", "inspect"]:
        return CompletedProcess(command, 0, stdout="[]", stderr="")
    if command[:2] == ["docker", "run"]:
        return CompletedProcess(command, 0, stdout="benign inspection", stderr="")
    raise AssertionError(f"unexpected subprocess command: {command}")

runner.subprocess.run = fake_run
try:
    temp_root = Path(tempfile.mkdtemp(prefix="codex-stage21-static-"))
    output_root = temp_root / "controlled_dynamic"
    runner.OUTPUT_ROOT = output_root
    runner.REPORTS_DIR = output_root / "reports"
    runner.QUARANTINE_DIR = output_root / "quarantine"
    report = runner.run_candidate(
        "ideation.zip",
        Path("analysis_results/real_skill_intake/inbox"),
        require_human_approved=True,
    )
finally:
    runner.subprocess.run = original_run

assert calls[0][:3] == ["docker", "image", "inspect"], calls
assert calls[1][:2] == ["docker", "run"], calls
assert report["execution_performed"] is True, report
assert report["container_started"] is True, report
assert report["container_removed"] is True, report
assert report["network_mode"] == "none", report
assert report["docker_sock_mounted"] is False, report
assert report["privileged"] is False, report
assert report["network_host"] is False, report
assert report["real_tokens_passed_to_container"] is False, report
assert report["uploaded_scripts_executed"] is False, report
assert report["codex_executed"] is False, report
assert report["strace_executed"] is False, report
assert report["hardening_policy_version"] == "stage22-runtime-hardening-v1", report
assert report["no_new_privileges"] is True, report
assert report["cap_drop_all"] is True, report
assert report["read_only_rootfs"] is True, report
assert report["pids_limit"] == "256", report
assert report["memory_limit"] == "512m", report
assert report["cpu_limit"] == "1.0", report
assert report["docker_network_none"] is True, report
assert report["docker_network_host_forbidden"] is True, report
assert report["docker_sock_forbidden"] is True, report
assert report["privileged_forbidden"] is True, report
assert report["real_home_forbidden"] is True, report
assert report["real_codex_home_forbidden"] is True, report
assert report["real_token_forbidden"] is True, report
assert report["uploaded_script_execution_forbidden"] is True, report
assert report["install_command_forbidden"] is True, report
assert report["docker_pull_forbidden"] is True, report
assert report["local_image_preflight_required"] is True, report
assert report["sanitized_env_required"] is True, report
assert report["runtime_audit_complete"] is True, report

if temp_root.exists():
    shutil.rmtree(temp_root)

print("Codex real skill controlled dynamic static test passed.")
PY

echo "Codex real skill controlled dynamic static test passed."
