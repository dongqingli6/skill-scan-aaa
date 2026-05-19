#!/bin/bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/sandbox/smoke_models.py \
  code/platforms/codex/sandbox/codex_command.py \
  code/platforms/codex/sandbox/smoke_runner.py \
  code/agent_skill_scan.py

unset OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN CODEX_HOME SSH_AUTH_SOCK ALLOW_CODEX_SAFE_SMOKE_TEST || true

python3 code/agent_skill_scan.py \
  --platform codex \
  --root code/platforms/codex/examples/safe_skill \
  --mode dynamic \
  --safe-smoke-test \
  --safe-skill-only \
  --output-dir analysis_results/codex_safe_smoke_plan

python3 - <<'PY'
import json
from pathlib import Path

base = Path("analysis_results/codex_safe_smoke_plan")
assert base.exists(), "missing output dir"

plan = base / "smoke_test_plan.json"
result = base / "smoke_test_result.json"
assert plan.exists(), "missing smoke_test_plan.json"
assert result.exists(), "missing smoke_test_result.json"

p = json.loads(plan.read_text(encoding="utf-8"))
r = json.loads(result.read_text(encoding="utf-8"))

assert p.get("safe_skill_only") is True
assert p.get("network_enabled") is False
assert r.get("attempted") is True
assert r.get("performed") is False, "plan-only test must not run codex"

print("Codex safe smoke plan-only test passed.")
PY
