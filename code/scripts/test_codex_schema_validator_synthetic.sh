#!/usr/bin/env bash
set -euo pipefail

tmp=/tmp/codex_schema_validator_synthetic
rm -rf "$tmp"
mkdir -p "$tmp"

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

tmp = Path("/tmp/codex_schema_validator_synthetic")
reports = {
    "dynamic_evidence.json": {
        "docker_network_mode": "none",
        "filesystem_diff_summary": {},
        "trace_summary": {},
        "syscall_policy_summary": {},
        "network_disabled_summary": {},
        "final_verdict": "synthetic valid report",
        "malicious_samples_executed": False,
    },
    "violation_report.json": {
        "violations": [],
        "severity_counts": {"LOW": 0, "HIGH": 0, "CRITICAL": 0},
        "matched_policy_rules": {},
        "enforcement_action": "record",
        "container_killed_by_monitor": False,
        "runtime_response": {},
        "fake_kill_called": False,
        "fake_kill_container_name": None,
    },
    "runtime_enforcement_report.json": {
        "container_started": False,
        "container_removed": True,
        "container_killed_by_monitor": False,
        "run_status": None,
        "timeout_observed": False,
        "enforcement_action": None,
        "runtime_response": {},
        "high_risk_syscalls": [],
        "critical_risk_syscalls": [],
        "matched_policy_rules": {},
        "final_verdict": "synthetic valid runtime report",
    },
    "final_security_report.json": {
        "static_summary": {},
        "dynamic_evidence": {},
        "runtime_enforcement": {},
        "syscall_policy_summary": {},
        "risk_summary": {},
        "final_verdict": "synthetic valid final report",
        "safety_boundaries": {},
    },
}
for name, data in reports.items():
    (tmp / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
(tmp / "invalid_dynamic_evidence.json").write_text(json.dumps({"docker_network_mode": "none"}), encoding="utf-8")
PY

python3 - <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path("code").resolve()))

from platforms.codex.enforcer.schema.schema_validator import validate_report_file

tmp = Path("/tmp/codex_schema_validator_synthetic")
schema_dir = Path("code/platforms/codex/enforcer/schema")
pairs = [
    ("dynamic_evidence.json", "dynamic_evidence_schema.json"),
    ("violation_report.json", "violation_report_schema.json"),
    ("runtime_enforcement_report.json", "runtime_enforcement_report_schema.json"),
    ("final_security_report.json", "final_security_report_schema.json"),
]
for report, schema in pairs:
    result = validate_report_file(tmp / report, schema_dir / schema)
    assert result["valid"] is True, (report, result)

invalid = validate_report_file(tmp / "invalid_dynamic_evidence.json", schema_dir / "dynamic_evidence_schema.json")
assert invalid["valid"] is False, invalid
assert "final_verdict" in invalid["missing_required_keys"], invalid

script_text = Path("code/scripts/test_codex_schema_validator_synthetic.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec", "strace" + " "]:
    assert forbidden not in script_text, f"schema validator test must not run {forbidden}"

print("Codex schema validator synthetic test passed.")
PY

echo "Codex schema validator synthetic test passed."
