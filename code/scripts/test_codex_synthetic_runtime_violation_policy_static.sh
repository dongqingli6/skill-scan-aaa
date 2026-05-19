#!/usr/bin/env bash
set -euo pipefail

# Stage 24 runtime violation policy static test.
# This test does not run Docker, Codex, strace, real skills, network commands,
# uploaded scripts, or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

policy_path = Path("code/platforms/codex/enforcer/runtime_violation/runtime_violation_policy.py")
assert policy_path.exists(), "runtime_violation_policy.py missing"
text = policy_path.read_text(encoding="utf-8")
assert "shell=True" not in text, "shell=True is forbidden"
assert "eval(" not in text, "eval is forbidden"
tree = ast.parse(text, filename=str(policy_path))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval is forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True is forbidden")

spec = importlib.util.spec_from_file_location("runtime_violation_policy", policy_path)
policy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(policy)

def event(event_type: str) -> dict[str, object]:
    return {
        "event_id": f"test-{event_type}",
        "timestamp": "2026-05-10T00:00:00+00:00",
        "sample_name": "synthetic",
        "container_name": "codex-synthetic-violation-container",
        "event_type": event_type,
        "observed_action": "synthetic",
        "target": "synthetic-target",
        "source": "static-test",
        "dry_run": True,
        "synthetic": True,
        "evidence": {},
    }

for event_type in [
    "docker_socket_access",
    "privileged_container_requested",
    "host_network_requested",
    "real_token_exposure",
    "ssh_key_read",
    "real_codex_home_read",
    "real_agents_home_read",
]:
    finding = policy.classify_runtime_event(event(event_type))
    assert finding["severity"] == "CRITICAL", finding

for event_type in [
    "outbound_network_attempt",
    "forbidden_path_read",
    "uploaded_script_execution_attempt",
    "docker_pull_attempt",
    "codex_exec_attempt",
    "strace_attempt",
]:
    finding = policy.classify_runtime_event(event(event_type))
    assert finding["severity"] == "HIGH", finding

medium = policy.classify_runtime_event(event("suspicious_shell_pattern"))
low = policy.classify_runtime_event(event("benign_denied_operation"))
critical_decision = policy.decide_runtime_response([policy.classify_runtime_event(event("docker_socket_access"))])
high_decision = policy.decide_runtime_response([policy.classify_runtime_event(event("docker_pull_attempt"))])
medium_decision = policy.decide_runtime_response([medium])
low_decision = policy.decide_runtime_response([low])

assert critical_decision["runtime_response"] == "kill_container", critical_decision
assert high_decision["runtime_response"] in {"kill_container", "fail_closed"}, high_decision
assert medium_decision["runtime_response"] == "fail_closed", medium_decision
assert low_decision["runtime_response"] == "record_only", low_decision

print("Codex synthetic runtime violation policy static test passed.")
PY

echo "Codex synthetic runtime violation policy static test passed."
