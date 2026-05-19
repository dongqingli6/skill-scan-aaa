#!/usr/bin/env bash
set -euo pipefail

# Stage 28 sinkhole policy static test.
# No Docker, Codex, Claude Code, strace, real API, or real internet.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

root = Path("code/platforms/codex/controlled_network")
for name in ["sinkhole_server.py", "sinkhole_policy.py", "sinkhole_report.py"]:
    path = root / name
    assert path.exists(), f"{name} missing"
    text = path.read_text(encoding="utf-8")
    assert "subprocess" not in text
    assert "shell=True" not in text
    assert "urllib.request" not in text
    tree = ast.parse(text, filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(alias.name != "requests" for alias in node.names), path
        if isinstance(node, ast.ImportFrom):
            assert node.module != "requests", path
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval forbidden in {path}")

sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("sinkhole_policy", root / "sinkhole_policy.py")
policy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(policy)
assert policy.evaluate_sinkhole_destination("http://127.0.0.1/a")["allowed"] is True
assert policy.evaluate_sinkhole_destination("http://localhost/a")["allowed"] is True
assert policy.evaluate_sinkhole_destination("http://sinkhole.local/a")["allowed"] is True
assert policy.evaluate_sinkhole_destination("https://example.com/a")["allowed"] is False
assert policy.evaluate_sinkhole_destination("http://169.254.169.254/latest")["allowed"] is False

spec = importlib.util.spec_from_file_location("sinkhole_server", root / "sinkhole_server.py")
server = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(server)
recorder = server.InMemorySinkhole("synthetic", 1, ["sk-fake-stage28"])
event = recorder.record_request(method="POST", url="http://127.0.0.1/capture", headers={"Authorization": "secret"}, body="sk-fake-stage28")
assert event["forwarded_external"] is False
assert event["allowed_local_sinkhole"] is True
assert event["headers"]["Authorization"] == "<redacted>"
assert event["honeypot_present"] is True

print("Codex Stage 28 sinkhole policy static test passed.")
PY

echo "Codex Stage 28 sinkhole policy static test passed."
