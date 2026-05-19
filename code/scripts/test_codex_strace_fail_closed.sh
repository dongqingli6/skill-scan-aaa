#!/usr/bin/env bash
set -euo pipefail

bash -n code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh
unset ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST EXECUTE_DOCKER_SAFE_SMOKE ENABLE_STRACE EXECUTE_STRACE_SMOKE CODEX_BUNDLE_RO SKILL_PATH || true
set +e
bash code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh > /tmp/codex_strace_fail_closed.out 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -E "disabled|fail-closed|refusing|not enabled" /tmp/codex_strace_fail_closed.out >/dev/null
echo "Codex strace fail-closed test passed."
