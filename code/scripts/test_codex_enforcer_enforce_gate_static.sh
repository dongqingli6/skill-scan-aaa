#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/enforcer/runtime_executor.py \
  code/platforms/codex/enforcer/enforced_runner.py

python3 - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path("code").resolve()))
from platforms.codex.enforcer.runtime_policy import load_policy, validate_skill_path
from platforms.codex.enforcer.runtime_executor import build_enforced_docker_run_command, validate_docker_command

policy = load_policy("code/platforms/codex/enforcer/policy.yaml")

for path in [
    "code/platforms/codex/examples/prompt_injection_skill",
    "code/platforms/codex/examples/script_risk_skill",
    "code/platforms/codex/examples/agents_pollution_sample",
]:
    decision = validate_skill_path(policy, path)
    assert decision.allowed is False, (path, decision)

try:
    build_enforced_docker_run_command(
        policy=policy,
        skill_path="code/platforms/codex/examples/safe_skill",
        output_dir="/tmp/codex_enforce_gate_static",
        codex_bundle_ro="/tmp/definitely_missing_codex_bundle",
    )
    raise AssertionError("missing Codex bundle should fail closed")
except RuntimeError as exc:
    assert "Codex bundle directory does not exist" in str(exc), exc

for bad in [
    ["docker", "run", "--privileged", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges"],
    ["docker", "run", "--network", "host", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges"],
    ["docker", "run", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "-v", "/var/run/docker.sock:/var/run/docker.sock"],
]:
    try:
        validate_docker_command(bad)
        raise AssertionError(f"bad docker command should fail: {bad}")
    except RuntimeError:
        pass
PY

if grep -R "shell=True" code/platforms/codex/enforcer; then
  echo "forbidden shell=True found" >&2
  exit 1
fi

echo "Codex enforcer enforce gate static test passed."
