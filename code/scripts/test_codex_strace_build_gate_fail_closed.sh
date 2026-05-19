#!/usr/bin/env bash
set -euo pipefail

bash -n code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh

unset ALLOW_STRACE_DOCKER_BUILD EXECUTE_STRACE_SMOKE || true
unset SSH_AUTH_SOCK OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN CODEX_HOME || true

ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST=1 \
EXECUTE_DOCKER_SAFE_SMOKE=1 \
ENABLE_STRACE=1 \
CODEX_BUNDLE_RO=/home/empty/.nvm/versions/node/v22.22.2 \
DOCKER_CMD="sudo docker" \
bash code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh \
  > /tmp/codex_strace_build_gate_fail_closed.out 2>&1

grep -E "disabled|fail-closed|preview only|ALLOW_STRACE_DOCKER_BUILD|EXECUTE_STRACE_SMOKE" \
  /tmp/codex_strace_build_gate_fail_closed.out >/dev/null

echo "Codex strace build gate fail-closed test passed."
