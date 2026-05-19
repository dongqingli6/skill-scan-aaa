#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

path = Path(".gitignore")
assert path.exists()
text = path.read_text(encoding="utf-8")
for pattern in [
    ".env",
    "*.pem",
    "*.key",
    "*.gz",
    "*.tar.gz",
    "__pycache__/",
    "analysis_results/**/raw*",
    "analysis_results/**/inbox*",
    "analysis_results/**/unredacted*",
    "analysis_results/**/real_skill*",
]:
    assert pattern in text, pattern
print("Codex open source release gitignore static test passed.")
PY

echo "Codex open source release gitignore static test passed."
