#!/usr/bin/env bash
set -euo pipefail

echo "===== DOCKER MANUAL SAFE SMOKE SCRIPT ====="
sed -n '1,360p' code/scripts/run_codex_docker_safe_smoke_MANUAL.sh

echo "===== FORBIDDEN PATTERN CHECK ====="
grep -R -n -E -e "--privileged|--network host|--network=host|--yolo|danger-full-access|dangerously|curl|wget|npm install|pip install|bash -c|claude -p" code/scripts/run_codex_docker_safe_smoke_MANUAL.sh || true

echo "===== CODEX EXEC ARG CHECK ====="
grep -R -n -E -e "--ask-for-approval|--sandbox|--ignore-user-config|--ignore-rules|--skip-git-repo-check|--ephemeral" code/scripts/run_codex_docker_safe_smoke_MANUAL.sh || true

echo "===== EXECUTION COMMAND CHECK ====="
grep -R -n -E -e "docker build|docker run|codex exec|CODEX_BUNDLE_RO|DOCKER_CMD|ALLOW_CODEX_DOCKER_SAFE_SMOKE_TEST|EXECUTE_DOCKER_SAFE_SMOKE" code/scripts/run_codex_docker_safe_smoke_MANUAL.sh || true
