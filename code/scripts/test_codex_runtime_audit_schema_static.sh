#!/usr/bin/env bash
set -euo pipefail

# Stage 22 runtime audit schema static test.
# This test reads JSON schema only. It does not run Docker, Codex, strace,
# real skills, uploaded scripts, network commands, or installers.

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

path = Path("code/platforms/codex/enforcer/hardening/runtime_audit_schema.json")
assert path.exists(), "runtime audit schema missing"
schema = json.loads(path.read_text(encoding="utf-8"))
required = set(schema.get("required", []))
properties = set(schema.get("properties", {}))

for field in [
    "network_mode",
    "docker_pull_executed",
    "image_present_locally",
    "no_new_privileges",
    "cap_drop_all",
    "read_only_rootfs",
    "pids_limit",
    "memory_limit",
    "cpu_limit",
    "final_verdict",
    "container_started",
    "container_removed",
]:
    assert field in required, f"missing required field: {field}"
    assert field in properties, f"missing schema property: {field}"

for field in [
    "hardening_policy_version",
    "docker_network_none",
    "docker_network_host_forbidden",
    "docker_sock_forbidden",
    "privileged_forbidden",
    "real_home_forbidden",
    "real_codex_home_forbidden",
    "real_token_forbidden",
    "uploaded_script_execution_forbidden",
    "install_command_forbidden",
    "docker_pull_forbidden",
    "local_image_preflight_required",
    "sanitized_env_required",
    "runtime_audit_complete",
]:
    assert field in required, f"missing Stage 22 required audit field: {field}"
    assert field in properties, f"missing Stage 22 schema property: {field}"

print("Codex runtime audit schema static test passed.")
PY

echo "Codex runtime audit schema static test passed."
