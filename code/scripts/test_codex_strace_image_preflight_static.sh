#!/usr/bin/env bash
set -euo pipefail

script="code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh"

bash -n "$script"

grep -F "DOCKER=(docker)" "$script" >/dev/null
grep -F "DOCKER=(sudo docker)" "$script" >/dev/null
grep -F "DOCKER=(sudo -n docker)" "$script" >/dev/null
grep -F 'STRACE_IMAGE="${STRACE_IMAGE:-codex-safe-smoke:strace}"' "$script" >/dev/null
grep -F 'BASE_IMAGE="${BASE_IMAGE:-ubuntu:24.04}"' "$script" >/dev/null
grep -F 'image inspect "$STRACE_IMAGE"' "$script" >/dev/null
grep -F 'image inspect "$BASE_IMAGE"' "$script" >/dev/null
grep -F "ALLOW_STRACE_DOCKER_BUILD" "$script" >/dev/null
grep -F "STRACE_IMAGE_PRESENT" "$script" >/dev/null
grep -F "BUILD_REQUIRED" "$script" >/dev/null
grep -F "STRACE_IMAGE_PRESENT=1" "$script" >/dev/null
grep -F "BUILD_REQUIRED=0" "$script" >/dev/null

if grep -E '(^|[^A-Za-z0-9_])docker[[:space:]]+image[[:space:]]+inspect' "$script" >/dev/null; then
  echo "found direct docker image inspect instead of DOCKER array" >&2
  exit 1
fi
if grep -E '(^|[^A-Za-z0-9_])docker[[:space:]]+build' "$script" >/dev/null; then
  echo "found direct docker build instead of DOCKER array" >&2
  exit 1
fi
if grep -E '(^|[^A-Za-z0-9_])docker[[:space:]]+run' "$script" >/dev/null; then
  echo "found direct docker run instead of DOCKER array" >&2
  exit 1
fi

echo "Codex strace image preflight static test passed."
