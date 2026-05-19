#!/usr/bin/env bash
set -euo pipefail

# Stage 13 local Web UI static guard.
# This test does not run Docker, Codex, strace, samples, or network-enabled work.

required_files=(
  "web_ui/app.py"
  "web_ui/safe_extract.py"
  "web_ui/job_store.py"
  "web_ui/backend_adapter.py"
  "web_ui/templates/index.html"
  "web_ui/templates/job.html"
  "web_ui/templates/report.html"
  "web_ui/static/style.css"
  "web_ui/README.md"
)

for path in "${required_files[@]}"; do
  [ -f "$path" ]
done

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

safe_extract = Path("web_ui/safe_extract.py").read_text(encoding="utf-8")
assert "relative_to" in safe_extract
assert "is_absolute" in safe_extract
assert '".."' in safe_extract or "'..'" in safe_extract
assert "symlink" in safe_extract.lower()
assert "islnk" in safe_extract
assert "MAX_FILES" in safe_extract
assert "MAX_TOTAL_BYTES" in safe_extract

for path in [Path("web_ui/app.py"), Path("web_ui/backend_adapter.py"), Path("web_ui/safe_extract.py")]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval is forbidden: {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

app_text = Path("web_ui/app.py").read_text(encoding="utf-8")
assert 'HOST = "127.0.0.1"' in app_text

backend_text = Path("web_ui/backend_adapter.py").read_text(encoding="utf-8")
app_text = Path("web_ui/app.py").read_text(encoding="utf-8")
dangerous_runtime_terms = [
    "docker build",
    "docker run",
    "codex exec",
    "strace ",
    "subprocess.run",
    "subprocess.Popen",
    "/var/run/docker.sock",
]
for text, label in [(backend_text, "backend_adapter.py"), (app_text, "app.py")]:
    for term in dangerous_runtime_terms:
        if term in text:
            raise AssertionError(f"forbidden runtime term {term!r} found in {label}")

for path in [Path("web_ui/app.py"), Path("web_ui/backend_adapter.py"), Path("web_ui/job_store.py")]:
    text = path.read_text(encoding="utf-8")
    for secret_name in ["sudo password", "OPENAI_API_KEY=", "ANTHROPIC_API_KEY=", "GITHUB_TOKEN="]:
        if secret_name in text:
            raise AssertionError(f"secret assignment marker found in {path}")

print("Codex Web UI static guard passed.")
PY

echo "Codex Web UI static test passed."
