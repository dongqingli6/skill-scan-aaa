#!/usr/bin/env bash
set -euo pipefail

# Stage 22 runtime hardening policy static test.
# This test reads policy text only. It does not run Docker, Codex, strace,
# real skills, uploaded scripts, network commands, or installers.

python3 - <<'PY'
from __future__ import annotations

from pathlib import Path

path = Path("code/platforms/codex/enforcer/hardening/runtime_hardening_policy.yaml")
assert path.exists(), "runtime hardening policy missing"
text = path.read_text(encoding="utf-8")

required = [
    "policy_version: stage22-runtime-hardening-v1",
    "network:",
    "  default: deny",
    "  docker_network_mode: none",
    "  host_network: forbidden",
    "  egress_allowlist_enabled: false",
    "  egress_proxy_enabled: false",
    "  dns_allowed: false",
    "filesystem:",
    "  sample_mount: read_only",
    "  output_mount: writable",
    "  docker_socket_mount: forbidden",
    "  host_home_mount: forbidden",
    "  real_codex_home_mount: forbidden",
    "  real_agents_home_mount: forbidden",
    "  env_file_mount: forbidden",
    "  ssh_key_mount: forbidden",
    "container:",
    "  privileged: forbidden",
    "  no_new_privileges: required",
    "  cap_drop_all: required",
    "  read_only_rootfs: preferred",
    "  pids_limit: required",
    "  memory_limit: required",
    "  cpu_limit: required",
    "  timeout: required",
    "execution:",
    "  codex_exec: forbidden",
    "  strace: forbidden_by_default",
    "  uploaded_scripts: forbidden",
    "  install_commands: forbidden",
    "  shell_eval: forbidden",
    "  shell_true: forbidden",
    "image:",
    "  allowlist_required: true",
    "  local_image_required: true",
    "  docker_pull: forbidden",
    "  image_inspect_before_run: required",
    "environment:",
    "  sanitized_subprocess_env: required",
    "  real_tokens_passed_to_container: forbidden",
    "audit:",
    "  runtime_event_log_required: true",
    "  container_start_record_required: true",
    "  container_cleanup_record_required: true",
    "  policy_decision_record_required: true",
    "  final_verdict_required: true",
]
for item in required:
    assert item in text, item

for notes in [
    "seccomp_policy_notes.md",
    "apparmor_policy_notes.md",
    "egress_policy_notes.md",
]:
    note_path = path.parent / notes
    assert note_path.exists(), f"missing hardening notes: {note_path}"

print("Codex runtime hardening policy static test passed.")
PY

echo "Codex runtime hardening policy static test passed."
