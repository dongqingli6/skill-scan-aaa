#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/sandbox/dynamic_evidence.py \
  code/platforms/codex/sandbox/network_verification.py \
  code/platforms/codex/sandbox/filesystem_diff_plan.py \
  code/platforms/codex/sandbox/strace_plan.py

python3 code/platforms/codex/sandbox/dynamic_evidence.py \
  --input-dir analysis_results/codex_docker_safe_smoke_manual
python3 code/platforms/codex/sandbox/network_verification.py \
  --input-dir analysis_results/codex_docker_safe_smoke_manual
python3 code/platforms/codex/sandbox/filesystem_diff_plan.py \
  --output-dir analysis_results/codex_docker_safe_smoke_manual
python3 code/platforms/codex/sandbox/strace_plan.py \
  --output-dir analysis_results/codex_docker_safe_smoke_manual

python3 - <<'PY'
import json
from pathlib import Path
base = Path("analysis_results/codex_docker_safe_smoke_manual")
required = [
    "dynamic_evidence.json",
    "network_disabled_verification.json",
    "filesystem_diff_plan.json",
    "strace_plan.json",
]
for name in required:
    path = base / name
    assert path.exists(), f"missing {name}"
    json.loads(path.read_text(encoding="utf-8"))
verification = json.loads((base / "network_disabled_verification.json").read_text(encoding="utf-8"))
assert verification["verification_status"] == "passed", verification
print("Codex dynamic evidence from smoke test passed.")
PY
