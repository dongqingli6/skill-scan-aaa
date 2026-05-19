#!/bin/bash
set -euo pipefail

python3 -m py_compile \
  code/core/models.py \
  code/platforms/codex/locator.py \
  code/platforms/codex/rules/codex_rules.py \
  code/platforms/codex/static_scan.py \
  code/platforms/codex/analyzer_adapter.py \
  code/platforms/codex/executor_adapter.py

python3 code/platforms/codex/static_scan.py \
  --root code/platforms/codex/examples \
  --output analysis_results/codex/static_scan_results.json

bash code/scripts/05_gen_agent_queue.sh codex code/platforms/codex/examples

bash code/scripts/06_agent_analyze.sh codex queues/codex_analysis_queue.jsonl

python3 - <<'PY'
import json, pathlib
paths = [
    "analysis_results/codex/static_scan_results.json",
    "analysis_results/codex/summary.json",
]
for p in paths:
    path = pathlib.Path(p)
    assert path.exists(), f"missing {p}"
    json.loads(path.read_text(encoding="utf-8"))
print("Codex static-only integration test passed.")
PY
