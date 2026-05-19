#!/bin/bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/sandbox/docker_smoke_models.py \
  code/platforms/codex/sandbox/docker_smoke_plan.py \
  code/platforms/codex/sandbox/docker_preflight.py \
  code/platforms/codex/sandbox/smoke_runner.py \
  code/agent_skill_scan.py

unset OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN CODEX_HOME SSH_AUTH_SOCK || true

python3 code/agent_skill_scan.py \
  --platform codex \
  --root code/platforms/codex/examples/safe_skill \
  --mode dynamic \
  --docker-smoke-plan \
  --docker-plan-only \
  --safe-skill-only \
  --output-dir analysis_results/codex_docker_smoke_plan

python3 - <<'PY'
import json
from pathlib import Path

base = Path("analysis_results/codex_docker_smoke_plan")
assert base.exists(), "missing output dir"

plan_path = base / "docker_smoke_plan.json"
preflight_path = base / "docker_preflight.json"

assert plan_path.exists(), "missing docker_smoke_plan.json"
assert preflight_path.exists(), "missing docker_preflight.json"

plan = json.loads(plan_path.read_text(encoding="utf-8"))
preflight = json.loads(preflight_path.read_text(encoding="utf-8"))

assert plan.get("plan_only") is True
assert plan.get("docker_build_allowed") is False
assert plan.get("docker_run_allowed") is False
assert plan.get("codex_exec_allowed") is False
assert plan.get("network_mode") == "none"
assert plan.get("sample_mount_mode") == "read-only"
assert preflight.get("ok") is True

cmd = plan.get("command_preview", "")
for bad in ["--privileged", "--network host", "--yolo", "danger-full-access", "dangerously", "curl", "wget", "npm install", "pip install"]:
    assert bad not in cmd, f"forbidden pattern in command_preview: {bad}"

print("Codex Docker smoke plan-only test passed.")
PY
