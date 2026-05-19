#!/usr/bin/env bash
set -euo pipefail

# Stage 15 Web UI real static scanner integration static guard.
# This test does not run Docker, Codex, strace, samples, or network-enabled work.

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

integration = Path("web_ui/static_scanner_integration.py")
backend = Path("web_ui/backend_adapter.py")
report = Path("web_ui/templates/report.html")

assert integration.exists(), "web_ui/static_scanner_integration.py missing"
integration_text = integration.read_text(encoding="utf-8")
backend_text = backend.read_text(encoding="utf-8")
report_text = report.read_text(encoding="utf-8")

for name in [
    "discover_real_static_scanner",
    "run_real_static_scanner",
    "normalize_static_findings",
    "fallback_to_prototype_adapter",
]:
    assert f"def {name}" in integration_text, f"{name} missing"

assert "static_scanner_integration" in backend_text, "backend_adapter does not import integration"
assert "static_scanner_mode" in backend_text, "backend_adapter does not write static_scanner_mode"
assert "Scanner mode" in report_text or "Scanner Mode" in report_text, "report does not display Scanner mode"

for path in [integration, backend, Path("web_ui/app.py")]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval is forbidden: {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

for text, label in [(integration_text, "static_scanner_integration.py"), (backend_text, "backend_adapter.py")]:
    forbidden = [
        "docker build",
        "docker run",
        "codex exec",
        "strace ",
        "run_pipeline.sh",
        "03_download.sh",
        "08_execute.sh",
        "run_skill.sh",
        "subprocess.run",
        "subprocess.Popen",
        "/var/run/docker.sock",
    ]
    for term in forbidden:
        if term in text:
            raise AssertionError(f"forbidden term {term!r} found in {label}")

print("Codex Web UI real static scanner static guard passed.")
PY

echo "Codex Web UI real static scanner static test passed."
