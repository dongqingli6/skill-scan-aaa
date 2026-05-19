#!/usr/bin/env bash
set -euo pipefail

bash -n code/scripts/run_codex_docker_safe_smoke_fs_diff_MANUAL.sh
unset ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST EXECUTE_DOCKER_SAFE_SMOKE ENABLE_FILESYSTEM_DIFF CODEX_BUNDLE_RO SKILL_PATH || true
set +e
bash code/scripts/run_codex_docker_safe_smoke_fs_diff_MANUAL.sh > /tmp/codex_fs_diff_fail_closed.out 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -E "disabled|fail-closed|refusing|not enabled" /tmp/codex_fs_diff_fail_closed.out >/dev/null

set +e
ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST=1 SKILL_PATH="code/platforms/codex/examples/prompt_injection_skill" bash code/scripts/run_codex_docker_safe_smoke_fs_diff_MANUAL.sh > /tmp/codex_fs_diff_non_safe.out 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -E "Refusing non-safe skill path|fail-closed|refusing" /tmp/codex_fs_diff_non_safe.out >/dev/null

echo "Codex filesystem diff fail-closed test passed."
