#!/usr/bin/env bash
set -euo pipefail

policy=code/platforms/codex/enforcer/syscall/syscall_policy.yaml
evaluator=code/platforms/codex/enforcer/syscall/syscall_policy.py

[ -f "$policy" ]
[ -f "$evaluator" ]

python3 -m py_compile \
  code/platforms/codex/enforcer/syscall/syscall_policy.py \
  code/platforms/codex/sandbox/strace_parser.py \
  code/platforms/codex/sandbox/trace_parser.py \
  code/platforms/codex/sandbox/dynamic_evidence_report.py \
  code/platforms/codex/enforcer/realtime_monitor.py \
  code/platforms/codex/enforcer/enforcement_report.py

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

policy_path = Path("code/platforms/codex/enforcer/syscall/syscall_policy.yaml")
evaluator_path = Path("code/platforms/codex/enforcer/syscall/syscall_policy.py")
policy_text = policy_path.read_text(encoding="utf-8")

for required in [
    "default_policy: deny_high_risk",
    "file_read",
    "file_write",
    "process_exec",
    "network",
    "privilege",
    "namespace",
    "kernel",
    "credential_access",
    "docker_escape",
    "/home/*/.ssh/**",
    "/home/*/.codex/**",
    "/home/*/.agents/**",
    "/**/.env",
    "/var/run/docker.sock",
    "/opt/codex-bundle/",
    "/workspace/safe_skill/",
    "mount",
    "umount",
    "pivot_root",
    "ptrace",
    "bpf",
    "perf_event_open",
    "keyctl",
    "add_key",
    "request_key",
    "init_module",
    "finit_module",
    "delete_module",
    "non_allowlisted_network_connect",
    "blocked_openai_network_none",
    "output_write",
    "safe_skill_read",
    "codex_bundle_read",
    "prototype",
]:
    assert required in policy_text, f"syscall policy missing {required}"

for path in [
    evaluator_path,
    Path("code/platforms/codex/sandbox/strace_parser.py"),
    Path("code/platforms/codex/sandbox/dynamic_evidence_report.py"),
    Path("code/platforms/codex/enforcer/realtime_monitor.py"),
    Path("code/platforms/codex/enforcer/enforcement_report.py"),
]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "eval":
                raise AssertionError(f"eval is forbidden: {path}")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

evaluator_source = evaluator_path.read_text(encoding="utf-8")
evaluator_tree = ast.parse(evaluator_source, filename=str(evaluator_path))
for node in ast.walk(evaluator_tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            assert alias.name not in {"socket", "urllib", "http.client", "requests", "subprocess", "os"}, alias.name
    if isinstance(node, ast.ImportFrom):
        assert (node.module or "") not in {"socket", "urllib", "http.client", "requests", "subprocess", "os"}, node.module
for forbidden in ["os.environ", "Path.home", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "SSH_AUTH_SOCK"]:
    assert forbidden not in evaluator_source, f"syscall_policy.py must not use {forbidden}"

script_text = Path("code/scripts/test_codex_syscall_policy_static.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec", "strace" + " "]:
    assert forbidden not in script_text, f"static test must not run {forbidden}"

print("Codex syscall policy static test passed.")
PY

echo "Codex syscall policy static test passed."
