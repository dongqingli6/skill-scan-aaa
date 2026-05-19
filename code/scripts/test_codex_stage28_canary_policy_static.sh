#!/usr/bin/env bash
set -euo pipefail

# Stage 28 canary honeypot static test.

python3 - <<'PY'
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

path = Path("code/platforms/codex/honeypot/canary_credentials.py")
report = Path("code/platforms/codex/honeypot/honeypot_report.py")
assert path.exists()
assert report.exists()
text = path.read_text(encoding="utf-8")
assert "BEGIN OPENSSH PRIVATE KEY" not in text
assert "BEGIN RSA PRIVATE KEY" not in text
assert "/home/empty" not in text
assert "sk-fake-" in text
assert "ghp_fake_" in text

spec = importlib.util.spec_from_file_location("canary_credentials", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
fake_home = Path("analysis_results/controlled_sinkhole_dynamic/test_fake_home")
if fake_home.exists():
    shutil.rmtree(fake_home)
canary = module.build_canary_credentials("sample.zip", 1, fake_home)
assert canary["honeypot_created"] is True
assert all("fake" in marker.lower() for marker in canary["markers"])
event = module.detect_honeypot_events(canary, [canary["markers"][0]], [canary["paths"]["env"]])
assert event["honeypot_touched"] is True
assert event["honeypot_exfiltrated"] is True

print("Codex Stage 28 canary policy static test passed.")
PY

echo "Codex Stage 28 canary policy static test passed."
