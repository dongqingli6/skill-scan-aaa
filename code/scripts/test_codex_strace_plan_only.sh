#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/sandbox/strace_models.py \
  code/platforms/codex/sandbox/strace_policy.py \
  code/platforms/codex/sandbox/strace_harness_plan.py \
  code/platforms/codex/sandbox/strace_parser.py

python3 code/platforms/codex/sandbox/strace_policy.py \
  --output-dir analysis_results/codex_strace_plan
python3 code/platforms/codex/sandbox/strace_harness_plan.py \
  --output-dir analysis_results/codex_strace_plan
python3 code/platforms/codex/sandbox/strace_parser.py \
  --input analysis_results/codex_strace_plan/nonexistent_strace.log \
  --output analysis_results/codex_strace_plan/strace_parse_result.json

python3 - <<'PY'
import json
from pathlib import Path
base = Path('analysis_results/codex_strace_plan')
for name in ['strace_policy.json', 'strace_harness_plan.json', 'strace_parse_result.json']:
    path = base / name
    assert path.exists(), f'missing {name}'
    json.loads(path.read_text(encoding='utf-8'))
plan = json.loads((base / 'strace_harness_plan.json').read_text(encoding='utf-8'))
assert plan['plan_only'] is True
assert plan['docker_run_allowed'] is False
assert plan['codex_exec_allowed'] is False
assert plan['strace_execution_allowed'] is False
assert plan['network_mode'] == 'none'
parse = json.loads((base / 'strace_parse_result.json').read_text(encoding='utf-8'))
assert parse['exists'] is False
print('Codex strace plan-only test passed.')
PY
