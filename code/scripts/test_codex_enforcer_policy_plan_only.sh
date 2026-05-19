#!/usr/bin/env bash
set -euo pipefail

policy=code/platforms/codex/enforcer/policy.yaml
bundle=/home/empty/.nvm/versions/node/v22.22.2
out=analysis_results/codex_runtime_enforcement/plan_only_test
mkdir -p "$out"

python3 -m py_compile \
  code/platforms/codex/enforcer/runtime_policy.py \
  code/platforms/codex/enforcer/docker_command_builder.py \
  code/platforms/codex/enforcer/enforced_runner.py

python3 code/platforms/codex/enforcer/enforced_runner.py \
  --skill-path code/platforms/codex/examples/safe_skill \
  --policy "$policy" \
  --codex-bundle-ro "$bundle" \
  --output-dir "$out/output" \
  --mode plan-only \
  --plan-output "$out/safe_skill_plan.json" >/tmp/codex_enforcer_safe_plan.out

for bad in prompt_injection_skill script_risk_skill agents_pollution_sample; do
  set +e
  python3 code/platforms/codex/enforcer/enforced_runner.py \
    --skill-path "code/platforms/codex/examples/$bad" \
    --policy "$policy" \
    --codex-bundle-ro "$bundle" \
    --output-dir "$out/output" \
    --mode plan-only \
    --plan-output "$out/${bad}_plan.json" >/tmp/codex_enforcer_${bad}.out 2>&1
  status=$?
  set -e
  [ "$status" -ne 0 ]
  grep -F "forbidden skill matched" "/tmp/codex_enforcer_${bad}.out" >/dev/null
done

python3 - <<'PY'
import json
from pathlib import Path

plan = json.loads(Path("analysis_results/codex_runtime_enforcement/plan_only_test/safe_skill_plan.json").read_text(encoding="utf-8"))
assert plan["policy_decision"]["allowed"] is True, plan
preview = plan["docker_command_preview"]["command_preview"]
for required in [
    "--network none",
    "--read-only",
    "--cap-drop ALL",
    "no-new-privileges",
    ":/workspace/safe_skill:ro",
    ":/output:rw",
    ":/opt/codex-bundle:ro",
]:
    assert required in preview, (required, preview)
for forbidden in ["--privileged", "--network host", "docker.sock"]:
    assert forbidden not in preview, (forbidden, preview)
assert plan["docker_command_preview"]["safety_errors"] == [], plan["docker_command_preview"]["safety_errors"]
PY

echo "Codex enforcer policy plan-only test passed."
