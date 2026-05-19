#!/usr/bin/env bash
set -euo pipefail

# Stage 28 dynamic evidence output static/controlled test.

python3 code/scripts/run_codex_stage28_controlled_dynamic_evidence.py \
  --samples ideation.zip react-effect-patterns.zip synthetic_canary_exfiltration_skill.zip synthetic_delayed_trigger_skill.zip synthetic_platform_config_touch_skill.zip \
  --enable-sinkhole \
  --enable-canary \
  --multi-session \
  --static-only false \
  --require-human-approved \
  --rounds 4 >/tmp/codex_stage28_dynamic_output_static.json

python3 - <<'PY'
from __future__ import annotations

import csv
import json
from pathlib import Path

cli = Path("code/scripts/run_codex_stage28_controlled_dynamic_evidence.py")
text = cli.read_text(encoding="utf-8")
assert "subprocess" not in text
assert "shell=True" not in text
assert "codex exec" not in text.lower()
assert "claude code" not in text.lower()
assert "strace " not in text.lower()
assert "docker run" not in text.lower()
assert "run_skill.sh" not in text.lower()
assert "install.sh" not in text.lower()
assert "setup.sh" not in text.lower()

root = Path("analysis_results/controlled_sinkhole_dynamic")
required = [
    "summary.json",
    "report.md",
    "risk_table.csv",
    "dynamic_evidence.json",
    "sinkhole_requests.json",
    "honeypot_events.json",
    "multi_session_report.json",
    "platform_surface_events.json",
    "final_dynamic_report.md",
]
for name in required:
    assert (root / name).exists(), f"{name} missing"

summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
assert summary["docker_executed"] is False
assert summary["codex_executed"] is False
assert summary["claude_code_executed"] is False
assert summary["strace_executed"] is False
assert summary["real_api_called"] is False
assert summary["real_internet_enabled"] is False
assert summary["network_enabled"] == "local_sinkhole_only"

evidence = json.loads((root / "dynamic_evidence.json").read_text(encoding="utf-8"))
required_fields = {
    "sample",
    "sinkhole_enabled",
    "canary_credentials_created",
    "honeypot_touched",
    "honeypot_exfiltrated",
    "multi_session_triggered",
    "platform_config_touched",
    "shadow_features",
    "touched_paths",
    "exfil_destinations",
    "final_verdict",
}
for item in evidence:
    assert required_fields.issubset(item), item
assert any(item["honeypot_exfiltrated"] for item in evidence)
assert any(item["platform_config_touched"] for item in evidence)
rows = list(csv.DictReader((root / "risk_table.csv").open(encoding="utf-8")))
assert rows

print("Codex Stage 28 dynamic output static test passed.")
PY

echo "Codex Stage 28 dynamic output static test passed."
