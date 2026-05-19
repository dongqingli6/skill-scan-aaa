#!/usr/bin/env bash
set -euo pipefail

python3 code/scripts/run_codex_open_source_release_package.py \
  --audit --sanitize --build-docs --build-demo-materials --build-competition-pack \
  --output analysis_results/opensource_release >/tmp/codex_opensource_docs_static.json

python3 - <<'PY'
from pathlib import Path

required = [
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/SAFETY_MODEL.md",
    "docs/STAGE_OVERVIEW.md",
    "docs/QUICK_START.md",
    "demo/demo_script.md",
    "competition_materials/PROJECT_INTRO.md",
    "competition_materials/INNOVATION_POINTS.md",
]
for rel in required:
    assert Path(rel).exists(), rel
readme = Path("README.md").read_text(encoding="utf-8")
for phrase in [
    "research prototype",
    "does not execute real malicious skills by default",
    "Mock/static provider paths are default",
    "Agent analysis cannot downgrade deterministic risk",
]:
    assert phrase in readme, phrase
print("Codex open source release docs static test passed.")
PY

echo "Codex open source release docs static test passed."
