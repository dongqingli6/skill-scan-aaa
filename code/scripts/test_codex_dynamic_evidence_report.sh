#!/usr/bin/env bash
set -euo pipefail

python3 code/platforms/codex/sandbox/dynamic_evidence_report.py >/tmp/codex_dynamic_evidence_report.out

json_path=analysis_results/codex_dynamic_security_report/dynamic_security_report.json
md_path=analysis_results/codex_dynamic_security_report/report.md

[ -f "$json_path" ]
[ -f "$md_path" ]

python3 - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("analysis_results/codex_dynamic_security_report/dynamic_security_report.json").read_text(encoding="utf-8"))
assert report["malicious_samples_executed"] is False, report
assert report["docker_network_mode"] == "none", report
assert report["real_tokens_present"] is False, report
assert report["sample_mount"] == "read-only", report
assert report["codex_bundle_mount"] == "read-only", report
PY

echo "Codex dynamic evidence report test passed."
