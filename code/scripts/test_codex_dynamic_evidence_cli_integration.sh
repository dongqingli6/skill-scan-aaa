#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/core/report_writer.py \
  code/agent_skill_scan.py

unset OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN CODEX_HOME SSH_AUTH_SOCK || true

evidence=analysis_results/codex_dynamic_security_report/dynamic_security_report.json
out=analysis_results/codex_cli_dynamic_integration

test -f "$evidence"

python3 code/agent_skill_scan.py \
  --platform codex \
  --root code/platforms/codex/examples/safe_skill \
  --mode static-only \
  --output-dir "$out" \
  --include-dynamic-evidence \
  --dynamic-evidence-path "$evidence" \
  >/tmp/codex_dynamic_evidence_cli_integration.out

test -f "$out/summary.json"
test -f "$out/report.md"

grep -F "Codex Dynamic Security Evidence" "$out/report.md" >/dev/null
grep -F "safe_skill only" "$out/report.md" >/dev/null
grep -F "malicious_samples_executed" "$out/report.md" >/dev/null
grep -F "docker_network_mode" "$out/report.md" >/dev/null
grep -F "strace_summary" "$out/report.md" >/dev/null
grep -E "HIGH=0|CRITICAL=0" "$out/report.md" >/dev/null

python3 - <<'PY'
import json
from pathlib import Path

summary = json.loads(Path("analysis_results/codex_cli_dynamic_integration/summary.json").read_text(encoding="utf-8"))
dynamic = summary.get("dynamic_evidence")
assert dynamic and dynamic["included"] is True, summary
assert dynamic["summary"]["malicious_samples_executed"] is False, dynamic
assert dynamic["summary"]["docker_network_mode"] == "none", dynamic
PY

echo "Codex dynamic evidence CLI integration test passed."
