#!/usr/bin/env bash
set -euo pipefail

# Stage 16 dynamic gate static guard.
# This test does not run Docker, Codex, strace, samples, or network-enabled work.

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

dynamic_gate = Path("web_ui/dynamic_gate.py")
runner = Path("web_ui/safe_dynamic_runner.py")
backend = Path("web_ui/backend_adapter.py")
app = Path("web_ui/app.py")
job_template = Path("web_ui/templates/job.html")

assert dynamic_gate.exists(), "web_ui/dynamic_gate.py missing"
assert runner.exists(), "web_ui/safe_dynamic_runner.py missing"

gate_text = dynamic_gate.read_text(encoding="utf-8")
runner_text = runner.read_text(encoding="utf-8")
backend_text = backend.read_text(encoding="utf-8")
app_text = app.read_text(encoding="utf-8")
job_text = job_template.read_text(encoding="utf-8")

for name in ["evaluate_dynamic_eligibility", "build_safe_dynamic_plan", "require_human_confirmation"]:
    assert f"def {name}" in gate_text, f"{name} missing"
assert "def run_safe_dynamic_execution" in runner_text, "run_safe_dynamic_execution missing"
assert "dynamic_gate" in backend_text, "backend_adapter does not import dynamic_gate"
assert "safe_dynamic_runner" in backend_text, "backend_adapter does not import safe_dynamic_runner"
assert "confirm_dynamic" in app_text, "confirm_dynamic route missing"
assert "run_safe_dynamic" in app_text, "run_safe_dynamic route missing"
assert "Dynamic Execution Gate" in job_text, "UI gate section missing"

for path in [dynamic_gate, runner, backend, app]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval is forbidden: {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

for text, label in [(gate_text, "dynamic_gate.py"), (runner_text, "safe_dynamic_runner.py"), (backend_text, "backend_adapter.py"), (app_text, "app.py")]:
    forbidden = [
        "--" + "privileged",
        "--network " + "host",
        "/var/run/docker.sock",
        "codex exec",
        "strace ",
        "prompt_injection_skill",
        "script_risk_skill",
        "agents_pollution_sample",
        "run_pipeline.sh",
        "03_download.sh",
        "08_execute.sh",
        "run_skill.sh",
    ]
    for term in forbidden:
        if term in text:
            raise AssertionError(f"forbidden term {term!r} found in {label}")

print("Codex Web UI dynamic gate static guard passed.")
PY

echo "Codex Web UI dynamic gate static test passed."
