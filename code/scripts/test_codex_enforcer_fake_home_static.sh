#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/enforcer/docker_command_builder.py \
  code/platforms/codex/enforcer/runtime_executor.py

python3 - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path("code").resolve()))
from platforms.codex.enforcer.docker_command_builder import build_docker_command_preview
from platforms.codex.enforcer.runtime_executor import build_enforced_docker_run_command
from platforms.codex.enforcer.runtime_policy import load_policy

policy = load_policy("code/platforms/codex/enforcer/policy.yaml")
common = {
    "policy": policy,
    "skill_path": "code/platforms/codex/examples/safe_skill",
    "output_dir": "/tmp/codex_fake_home_static_output",
    "codex_bundle_ro": "/home/empty/.nvm/versions/node/v22.22.2",
}
plan = build_docker_command_preview(**common)["command_preview"]
enforce = build_enforced_docker_run_command(**common)["command_preview"]
combined = plan + "\n" + enforce

for required in [
    "mkdir -p /home/codexsafe/.codex",
    "mkdir -p /home/codexsafe/.agents",
    "mkdir -p /output",
    "chmod 700 /home/codexsafe /home/codexsafe/.codex /home/codexsafe/.agents",
    "HOME=/home/codexsafe",
    "CODEX_HOME=/home/codexsafe/.codex",
]:
    assert required in combined, (required, combined)

for forbidden in [
    "/home/empty/.codex",
    "/home/empty/.agents",
    "SSH_AUTH_SOCK",
    "OPENAI_API_KEY",
]:
    assert forbidden not in combined, (forbidden, combined)
PY

if grep -R "shell=True" code/platforms/codex/enforcer; then
  echo "forbidden shell=True found" >&2
  exit 1
fi
if grep -R "eval" code/platforms/codex/enforcer; then
  echo "forbidden eval found" >&2
  exit 1
fi

echo "Codex enforcer fake HOME static test passed."
