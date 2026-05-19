#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import ast
import importlib.util
import sys
from pathlib import Path

path = Path("code/platforms/codex/human_review_labeling/evidence_collector.py")
assert path.exists()
text = path.read_text(encoding="utf-8")
assert "analysis_results" in text
for forbidden in ["subprocess", "docker run", "codex exec", "claude code", "strace ", "run_skill.sh", "urllib.request"]:
    assert forbidden not in text.lower(), forbidden
tree = ast.parse(text, filename=str(path))
for node in tree.body:
    if isinstance(node, ast.Import):
        assert all(alias.name != "requests" for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        assert node.module != "requests"
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell":
                raise AssertionError("shell keyword forbidden")

sys.path.insert(0, str(path.parent.resolve()))
spec = importlib.util.spec_from_file_location("evidence_collector", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
bundle = module.collect_evidence(Path(".").resolve(), include_real=True, include_synthetic=True)
assert "samples" in bundle
assert any(item["source_type"] == "real" for item in bundle["samples"])
assert any(item["source_type"] == "synthetic" for item in bundle["samples"])
assert "evidence_missing" in bundle
print("Codex human review evidence collector static test passed.")
PY

echo "Codex human review evidence collector static test passed."
