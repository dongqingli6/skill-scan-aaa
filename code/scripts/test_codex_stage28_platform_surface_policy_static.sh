#!/usr/bin/env bash
set -euo pipefail

# Stage 28 platform surface policy static test.

python3 - <<'PY'
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

root = Path("code/platforms/codex/platform_surface")
for name in ["platform_surface_monitor.py", "platform_surface_policy.py"]:
    assert (root / name).exists(), f"{name} missing"

sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("platform_surface_policy", root / "platform_surface_policy.py")
policy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(policy)
assert policy.classify_platform_touch(".codex/settings.json", "read")["severity"] == "medium"
assert policy.classify_platform_touch("approval_policy sandbox_mode network_access", "modify")["severity"] == "high"
assert policy.classify_platform_touch("ordinary.md", "read")["platform_config_touched"] is False

spec = importlib.util.spec_from_file_location("platform_surface_monitor", root / "platform_surface_monitor.py")
monitor = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(monitor)
events = monitor.monitor_platform_surface("synthetic", [{"operation": "modify", "target": ".mcp.json network_access"}])
assert events
assert events[0]["platform_config_touched"] is True
assert events[0]["policy_impact"] == "high"

print("Codex Stage 28 platform surface policy static test passed.")
PY

echo "Codex Stage 28 platform surface policy static test passed."
