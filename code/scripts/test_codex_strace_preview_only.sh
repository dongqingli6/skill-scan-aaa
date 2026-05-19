#!/usr/bin/env bash
set -euo pipefail

bash -n code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh

unset EXECUTE_DOCKER_SAFE_SMOKE ENABLE_STRACE EXECUTE_STRACE_SMOKE || true
unset SSH_AUTH_SOCK OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN CODEX_HOME || true

set +e
ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST=1 \
CODEX_BUNDLE_RO=/home/empty/.nvm/versions/node/v22.22.2 \
DOCKER_CMD="docker" \
bash code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh \
  > /tmp/codex_strace_preview_only.out 2>&1
status=$?
set -e

grep -E "Strace safe smoke preview|preview only|no Docker build|no Docker run|no Codex execution|no strace" \
  /tmp/codex_strace_preview_only.out >/dev/null
grep -F "DOCKER_CMD: docker" /tmp/codex_strace_preview_only.out >/dev/null
grep -F "STRACE_IMAGE=codex-safe-smoke:strace" /tmp/codex_strace_preview_only.out >/dev/null
grep -F "STRACE_IMAGE_PRESENT=1" /tmp/codex_strace_preview_only.out >/dev/null
grep -F "BUILD_REQUIRED=0" /tmp/codex_strace_preview_only.out >/dev/null
if grep -F "ubuntu:24.04 is not present locally" /tmp/codex_strace_preview_only.out >/dev/null; then
  echo "preview incorrectly reported missing base image" >&2
  exit 1
fi
if [ "$status" -ne 0 ]; then
  echo "preview failed for an unexpected reason" >&2
  exit 1
fi

echo "Codex strace preview-only test passed."
