#!/bin/bash
#
# MANUAL ONLY: Codex safe_skill smoke test.
#
# - Only safe_skill is allowed.
# - This is only for checking fake HOME and whether Codex CLI can start.
# - Do not use this for malicious samples.
# - This script is fail-closed unless ALLOW_CODEX_SAFE_SMOKE_TEST=1 is set.
# - Do not pass real tokens or real HOME state.
# - If Codex is not installed or not logged in, let it fail and inspect stderr.
#

set -euo pipefail

if [ "$(basename "$PWD")" != "MaliciousAgentSkillsBench-Codex" ]; then
    echo "Run this only from MaliciousAgentSkillsBench-Codex." >&2
    exit 1
fi

SAFE_SKILL="code/platforms/codex/examples/safe_skill"
if [ ! -f "$SAFE_SKILL/SKILL.md" ]; then
    echo "safe_skill not found at expected path: $SAFE_SKILL" >&2
    exit 1
fi

if [ "${ALLOW_CODEX_SAFE_SMOKE_TEST:-}" != "1" ]; then
    echo "Refusing to run. Set ALLOW_CODEX_SAFE_SMOKE_TEST=1 manually." >&2
    exit 1
fi

python3 code/agent_skill_scan.py \
  --platform codex \
  --root code/platforms/codex/examples/safe_skill \
  --mode dynamic \
  --safe-smoke-test \
  --safe-skill-only \
  --allow-codex-exec \
  --output-dir analysis_results/codex_safe_smoke_manual
