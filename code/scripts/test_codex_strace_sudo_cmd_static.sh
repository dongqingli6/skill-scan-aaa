#!/usr/bin/env bash
set -euo pipefail

script="code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh"

bash -n "$script"

grep -F '"sudo -n docker")' "$script" >/dev/null
grep -F "DOCKER=(sudo -n docker)" "$script" >/dev/null
grep -F "sudo -n true" "$script" >/dev/null
grep -F '"${DOCKER[@]}"' "$script" >/dev/null

if grep -F "sudo -S" "$script" >/dev/null; then
  echo "forbidden sudo -S found" >&2
  exit 1
fi
if grep -F "askpass" "$script" >/dev/null; then
  echo "forbidden askpass found" >&2
  exit 1
fi
if grep -F "eval" "$script" >/dev/null; then
  echo "forbidden eval found" >&2
  exit 1
fi

echo "Codex strace sudo command static test passed."
