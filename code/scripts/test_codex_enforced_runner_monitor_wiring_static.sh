#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/enforcer/enforced_runner.py \
  code/platforms/codex/enforcer/runtime_executor.py \
  code/platforms/codex/enforcer/realtime_monitor.py \
  code/platforms/codex/enforcer/enforcement_report.py

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path


ENFORCER_FILES = [
    Path("code/platforms/codex/enforcer/enforced_runner.py"),
    Path("code/platforms/codex/enforcer/runtime_executor.py"),
    Path("code/platforms/codex/enforcer/realtime_monitor.py"),
    Path("code/platforms/codex/enforcer/enforcement_report.py"),
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


sources = {path: read(path) for path in ENFORCER_FILES}
runner = sources[Path("code/platforms/codex/enforcer/enforced_runner.py")]
executor = sources[Path("code/platforms/codex/enforcer/runtime_executor.py")]
monitor = sources[Path("code/platforms/codex/enforcer/realtime_monitor.py")]
report = sources[Path("code/platforms/codex/enforcer/enforcement_report.py")]

assert "PollingMonitor" in runner, "enforced_runner must import/use PollingMonitor"
assert "monitor.start()" in runner, "enforce mode must start realtime monitor"
assert "start_container(command_info[\"command\"]" in runner, "enforce mode must start runtime executor command"
assert "container_name=command_info[\"container_name\"]" in runner, "monitor must receive container_name"
assert "runtime_response=runtime_response" in runner, "monitor must receive policy runtime_response"
assert "kill_on_high=kill_on_high" in runner, "monitor must receive kill_on_high"
assert "kill_callback=on_violation" in runner, "monitor must receive kill callback"
assert "kill_container(args.docker_cmd, command_info[\"container_name\"]" in runner, "HIGH/CRITICAL path must kill container"
assert "container_killed_by_monitor" in runner, "runner must track monitor kill state"
assert "kill_events" in runner, "runner must record docker kill results"

assert "container_name" in monitor, "monitor must know container_name"
assert "kill_on_high" in monitor, "monitor must support kill_on_high"
assert "runtime_response" in monitor, "monitor must use policy runtime_response"
assert "action_key = f\"on_{event['severity'].lower()}_violation\"" in monitor, "monitor must map severity to policy action"
assert "kill_container" in monitor, "monitor events must carry kill_container enforcement action"
assert "self.kill_callback(event)" in monitor, "monitor must invoke kill callback"
assert "strace.log*" in monitor, "monitor must scan strace.log / strace.log.*"

assert "subprocess.run(" in executor, "runtime executor must use subprocess"
assert "[docker_cmd, \"kill\", container_name]" in executor, "docker kill must use subprocess argument list"
assert "check=False" in executor, "docker kill must inspect return code explicitly"
assert "raise RuntimeError(f\"docker kill failed" in executor, "docker kill failure must fail closed"

assert "container_started" in report, "report must record container_started"
assert "container_removed" in report, "report must record container_removed"
assert "container_killed_by_monitor" in report, "report must record container_killed_by_monitor"
assert "violations" in report, "report must record violations"
assert "enforcement_actions" in report, "report must record enforcement actions"
assert "risk_summary" in report and "HIGH" in report and "CRITICAL" in report, "report must record risk summary"
assert "enforcement_action" in monitor, "monitor events must record enforcement_action"

for path, source in sources.items():
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "eval":
                raise AssertionError(f"eval is forbidden: {path}")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

command_slice = executor[executor.index("command = [") : executor.index("validate_docker_command(command)")]
assert "--privileged" not in command_slice, "Docker run command must not use --privileged"
assert "--network host" not in command_slice, "Docker run command must not use --network host"
assert "/var/run/docker.sock" not in command_slice, "Docker run command must not mount docker.sock"
assert "OPENAI_API_KEY" not in command_slice, "Docker run command must not pass real OPENAI_API_KEY"
assert "ANTHROPIC_API_KEY" not in command_slice, "Docker run command must not pass real ANTHROPIC_API_KEY"
assert "GITHUB_TOKEN" not in command_slice, "Docker run command must not pass real GITHUB_TOKEN"
assert "HOME=/home/codexsafe" in command_slice, "Docker run command must use fake HOME"
assert "CODEX_HOME=/home/codexsafe/.codex" in command_slice, "Docker run command must use fake CODEX_HOME"

print("Codex enforced runner monitor wiring static test passed.")
PY
