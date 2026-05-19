#!/usr/bin/env bash
set -euo pipefail

# Stage 25A schema/prompt static test.
# This test does not run Docker, Codex, Claude Code, strace, real skills,
# network commands, uploaded scripts, or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

root = Path("code/platforms/codex/agent_static_analysis")
schema_path = root / "agent_static_schema.json"
prompt_path = root / "agent_static_prompt.md"
assert schema_path.exists(), "agent static schema missing"
assert prompt_path.exists(), "agent static prompt missing"

schema = json.loads(schema_path.read_text(encoding="utf-8"))
required = set(schema.get("required", []))
for field in [
    "agent_name",
    "analysis_mode",
    "sample_name",
    "files_reviewed",
    "risk_summary",
    "findings",
    "recommended_gate",
    "can_execute_dynamically",
    "requires_human_review",
    "agent_failed",
    "parse_error",
    "timeout",
    "notes",
]:
    assert field in required, field

prompt = prompt_path.read_text(encoding="utf-8").lower()
assert "untrusted skill content" in prompt
assert "do not execute code" in prompt
assert "return json only" in prompt
assert "do not downgrade deterministic scanner findings" in prompt
assert "prompt injection" in prompt
assert "docker.sock" in prompt

print("Codex agent static analysis schema static test passed.")
PY

echo "Codex agent static analysis schema static test passed."
