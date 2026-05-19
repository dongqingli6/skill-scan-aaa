#!/usr/bin/env bash
set -euo pipefail

# Stage 14 Web UI polish static guard.
# This test does not run Docker, Codex, strace, samples, or network-enabled work.

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

app = Path("web_ui/app.py").read_text(encoding="utf-8")
adapter = Path("web_ui/backend_adapter.py").read_text(encoding="utf-8")
job_store = Path("web_ui/job_store.py").read_text(encoding="utf-8")
job_template = Path("web_ui/templates/job.html").read_text(encoding="utf-8")
report_template = Path("web_ui/templates/report.html").read_text(encoding="utf-8")

for route in [
    "download/static_report_md",
    "download/static_report_json",
    "download/dynamic_plan_md",
    "download/dynamic_plan_json",
]:
    assert route.split("/", 1)[1] in app, f"missing download route marker: {route}"

assert "/delete" in app, "delete job route missing"
assert "Delete Job" in job_template, "delete job button missing"
assert "confirm(" in job_template, "delete confirmation prompt missing"
assert "JOB_ID_RE" in job_store and "[A-Za-z0-9_-]" in job_store, "job_id validation missing"
assert "render_file_tree" in app and "truncated after 100 paths" in app, "file tree preview missing"
assert "suppressed" in adapter and "NEGATIVE_CONTEXT_PATTERNS" in adapter, "false-positive suppression missing"
assert "Suppressed documentation-only match" in adapter, "suppressed report text missing"
assert "Human-readable Summary" in report_template, "human-readable report summary missing"
assert "Risk Summary" in job_template and "risk_cards" in job_template, "risk cards missing"

for path in [Path("web_ui/app.py"), Path("web_ui/backend_adapter.py"), Path("web_ui/job_store.py")]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval is forbidden: {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

for text, label in [(app, "app.py"), (adapter, "backend_adapter.py")]:
    forbidden_runtime_terms = [
        "docker build",
        "docker run",
        "codex exec",
        "strace ",
        "subprocess.run",
        "subprocess.Popen",
        "/var/run/docker.sock",
    ]
    for term in forbidden_runtime_terms:
        if term in text:
            raise AssertionError(f"forbidden runtime term {term!r} found in {label}")

print("Codex Web UI polish static guard passed.")
PY

echo "Codex Web UI polish static test passed."
