#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile code/platforms/codex/enforcer/violation_monitor.py

python3 code/platforms/codex/enforcer/violation_monitor.py \
  --dynamic-evidence-path analysis_results/codex_dynamic_security_report/dynamic_security_report.json \
  --strace-path analysis_results/codex_strace_plan/strace_parse_result.json \
  --filesystem-diff-path analysis_results/codex_docker_safe_smoke_fs_diff_manual/filesystem_diff.json \
  --network-path analysis_results/codex_docker_safe_smoke_manual/network_disabled_verification.json \
  --output analysis_results/codex_runtime_enforcement/violation_report.json >/tmp/codex_violation_monitor.out

python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("analysis_results/codex_runtime_enforcement/violation_report.json").read_text(encoding="utf-8"))
assert report["risk_summary"]["HIGH"] == 0, report["risk_summary"]
assert report["risk_summary"]["CRITICAL"] == 0, report["risk_summary"]
assert report["blocked_network_attempts_are_blocked"] is True, report
assert report["real_network_connect_success_observed"] is False, report
assert report["real_sensitive_read_observed"] is False, report
assert report["readonly_mount_write_observed"] is False, report
categories = {item["category"] for item in report["violations"]}
assert "blocked_network_attempt" in categories, categories
PY

echo "Codex violation monitor existing evidence test passed."
