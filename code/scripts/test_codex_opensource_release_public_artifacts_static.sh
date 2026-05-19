#!/usr/bin/env bash
set -euo pipefail

python3 code/scripts/run_codex_open_source_release_package.py \
  --audit --sanitize --build-docs --build-demo-materials --build-competition-pack \
  --output analysis_results/opensource_release >/tmp/codex_opensource_public_static.json

python3 - <<'PY'
from pathlib import Path

root = Path("public_artifacts")
assert root.exists()
files = [path for path in root.rglob("*") if path.is_file()]
assert files
for path in files:
    name = path.name.lower()
    assert name != ".env"
    assert not name.endswith((".pem", ".key", ".gz", ".tar.gz", ".zip"))
    text = path.read_text(encoding="utf-8", errors="ignore")
    assert "OPENAI_API_KEY=" not in text
    assert "ANTHROPIC_API_KEY=" not in text
    assert "GITHUB_TOKEN=" not in text
    assert "/home/empty" not in text
assert (root / "scaled_metrics.json").exists()
assert (root / "stage29_summary.json").exists()
print("Codex open source release public artifacts static test passed.")
PY

echo "Codex open source release public artifacts static test passed."
