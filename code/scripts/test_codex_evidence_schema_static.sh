#!/usr/bin/env bash
set -euo pipefail

schema_dir=code/platforms/codex/enforcer/schema

for name in \
  dynamic_evidence_schema.json \
  violation_report_schema.json \
  runtime_enforcement_report_schema.json \
  final_security_report_schema.json; do
  [ -f "$schema_dir/$name" ]
done
[ -f "$schema_dir/schema_validator.py" ]

python3 -m py_compile \
  code/platforms/codex/enforcer/schema/schema_validator.py \
  code/platforms/codex/enforcer/synthetic/attack_matrix_runner.py

python3 - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

schema_dir = Path("code/platforms/codex/enforcer/schema")
required_by_schema = {
    "dynamic_evidence_schema.json": [
        "docker_network_mode",
        "filesystem_diff_summary",
        "trace_summary",
        "syscall_policy_summary",
        "network_disabled_summary",
        "final_verdict",
        "malicious_samples_executed",
    ],
    "violation_report_schema.json": [
        "violations",
        "severity_counts",
        "matched_policy_rules",
        "enforcement_action",
        "container_killed_by_monitor",
        "runtime_response",
        "fake_kill_called",
        "fake_kill_container_name",
    ],
    "runtime_enforcement_report_schema.json": [
        "container_started",
        "container_removed",
        "container_killed_by_monitor",
        "run_status",
        "timeout_observed",
        "enforcement_action",
        "runtime_response",
        "high_risk_syscalls",
        "critical_risk_syscalls",
        "matched_policy_rules",
        "final_verdict",
    ],
    "final_security_report_schema.json": [
        "static_summary",
        "dynamic_evidence",
        "runtime_enforcement",
        "syscall_policy_summary",
        "risk_summary",
        "final_verdict",
        "safety_boundaries",
    ],
}
for filename, required_keys in required_by_schema.items():
    schema = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
    assert schema["status"] == "prototype_only", schema
    for key in required_keys:
        assert key in schema["required"], (filename, key, schema["required"])

for path in [
    Path("code/platforms/codex/enforcer/schema/schema_validator.py"),
    Path("code/platforms/codex/enforcer/synthetic/attack_matrix_runner.py"),
]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "eval":
                raise AssertionError(f"eval is forbidden: {path}")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")
    for forbidden in ["subprocess", "os.environ", "Path.home", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN"]:
        assert forbidden not in source, f"{path} must not use {forbidden}"

script_text = Path("code/scripts/test_codex_evidence_schema_static.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec", "strace" + " "]:
    assert forbidden not in script_text, f"static test must not run {forbidden}"

print("Codex evidence schema static test passed.")
PY

echo "Codex evidence schema static test passed."
