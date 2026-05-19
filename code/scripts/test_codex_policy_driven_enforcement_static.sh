#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/enforcer/realtime_monitor.py \
  code/platforms/codex/enforcer/enforced_runner.py \
  code/platforms/codex/enforcer/enforcement_report.py \
  code/platforms/codex/enforcer/syscall/syscall_policy.py

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

files = [
    Path("code/platforms/codex/enforcer/realtime_monitor.py"),
    Path("code/platforms/codex/enforcer/enforced_runner.py"),
    Path("code/platforms/codex/enforcer/enforcement_report.py"),
    Path("code/platforms/codex/enforcer/syscall/syscall_policy.py"),
]
sources = {path: path.read_text(encoding="utf-8") for path in files}
monitor = sources[Path("code/platforms/codex/enforcer/realtime_monitor.py")]
runner = sources[Path("code/platforms/codex/enforcer/enforced_runner.py")]
report = sources[Path("code/platforms/codex/enforcer/enforcement_report.py")]

assert "classify_syscall_event" in monitor, "realtime_monitor must use syscall policy classification"
assert "load_syscall_policy" in monitor, "realtime_monitor must load syscall policy"
assert "matched_rule" in monitor, "monitor events must carry matched policy rule"
assert "enforcement_action" in monitor, "monitor events must carry enforcement action"
assert '"kill_container" if severity in {"HIGH", "CRITICAL"} else "record"' in monitor
assert "kill_callback" in monitor, "monitor must support injected fake kill callback"
assert "self.kill_callback(event)" in monitor, "monitor must execute kill callback through testable seam"
assert "event[\"severity\"] in {\"HIGH\", \"CRITICAL\"}" in monitor, "monitor must gate kill decision on HIGH/CRITICAL"
assert "policy_action == \"kill_container\"" in monitor, "monitor must honor runtime policy action"

assert "kill_callback=on_violation" in runner, "production path must still wire docker kill callback"
assert "kill_container(args.docker_cmd" in runner, "production callback must still use docker kill helper"

for required in [
    "matched_policy_rules",
    "high_risk_syscalls",
    "critical_risk_syscalls",
    "enforcement_action",
    "enforcement_actions",
    "container_killed_by_monitor",
    "runtime_response",
]:
    assert required in report, f"enforcement_report missing {required}"

for path, source in sources.items():
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "eval":
                raise AssertionError(f"eval is forbidden: {path}")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

for forbidden in ["--privileged", "--network host", "/var/run/docker.sock:/var/run/docker.sock"]:
    assert forbidden not in monitor, f"monitor must not contain {forbidden}"
    assert forbidden not in report, f"report must not contain {forbidden}"

script_text = Path("code/scripts/test_codex_policy_driven_enforcement_static.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec", "strace" + " "]:
    assert forbidden not in script_text, f"static test must not run {forbidden}"

print("Codex policy-driven enforcement static test passed.")
PY

echo "Codex policy-driven enforcement static test passed."
