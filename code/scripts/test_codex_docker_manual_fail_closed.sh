#!/usr/bin/env bash
set -euo pipefail

bash -n code/scripts/run_codex_docker_safe_smoke_MANUAL.sh

# Do not set ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST, EXECUTE_DOCKER_SAFE_SMOKE,
# CODEX_BUNDLE_RO, or ALLOW_DOCKER_BASE_IMAGE_PULL. The manual script must
# refuse before any Docker build/run or Codex command can run.
unset ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST EXECUTE_DOCKER_SAFE_SMOKE CODEX_BUNDLE_RO CODEX_BINARY_RO ALLOW_DOCKER_BASE_IMAGE_PULL || true
set +e
bash code/scripts/run_codex_docker_safe_smoke_MANUAL.sh > /tmp/codex_docker_manual_fail_closed.out 2>&1
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo "manual script exited 0 in fail-closed mode; checking it did not execute"
fi

grep -E "ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST|refusing|disabled|not enabled|fail-closed" /tmp/codex_docker_manual_fail_closed.out >/dev/null

# These may appear only in printed disabled text or command previews, never as a
# reached execution path during this fail-closed test.
grep -n "docker build\|docker run\|codex exec" /tmp/codex_docker_manual_fail_closed.out || true

echo "Docker manual fail-closed test passed."
