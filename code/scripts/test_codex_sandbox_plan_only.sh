#!/bin/bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/sandbox/sandbox_models.py \
  code/platforms/codex/sandbox/fake_home.py \
  code/platforms/codex/sandbox/preflight.py \
  code/platforms/codex/sandbox/run_plan.py \
  code/agent_skill_scan.py

unset OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN CODEX_HOME SSH_AUTH_SOCK || true

python3 code/agent_skill_scan.py \
  --platform codex \
  --root code/platforms/codex/examples \
  --mode dynamic \
  --sandbox-plan-only \
  --output-dir analysis_results/codex_sandbox_plan

python3 - <<'PY'
import json
from pathlib import Path

base = Path("analysis_results/codex_sandbox_plan")
assert base.exists(), "missing sandbox plan output dir"

queue = base / "codex_run_queue.jsonl"
assert queue.exists(), "missing codex_run_queue.jsonl"

lines = [json.loads(x) for x in queue.read_text(encoding="utf-8").splitlines() if x.strip()]
assert lines, "empty run queue"

for item in lines:
    assert item.get("allow_dynamic_execution") is False
    assert item.get("network_enabled") is False
    assert item.get("fake_home_required") is True
    assert item.get("real_home_allowed") is False
    assert item.get("real_tokens_allowed") is False

plans = list(base.rglob("run_plan.json"))
preflights = list(base.rglob("preflight.json"))
assert plans, "missing run_plan.json files"
assert preflights, "missing preflight.json files"

print("Codex sandbox plan-only test passed.")
PY
