#!/usr/bin/env bash
set -euo pipefail

dockerfile="code/platforms/codex/sandbox/docker/Dockerfile.codex-strace-sandbox"

[ -f "$dockerfile" ]
grep -F "FROM ubuntu:24.04" "$dockerfile" >/dev/null
grep -F "apt-get install" "$dockerfile" >/dev/null
grep -F "strace ca-certificates" "$dockerfile" >/dev/null

for bad in "curl" "wget" "npm install" "pip install" "codex exec" "--privileged" "--network host" "--yolo" "danger-full-access" "dangerously"; do
  if grep -F -- "$bad" "$dockerfile" >/dev/null; then
    echo "forbidden pattern found in strace Dockerfile: $bad" >&2
    exit 1
  fi
done

grep -F "USER 1000:1000" "$dockerfile" >/dev/null
grep -F "CODEX_HOME=/home/codexsafe/.codex" "$dockerfile" >/dev/null
grep -F "/opt/codex-bundle/bin" "$dockerfile" >/dev/null
grep -F "/workspace" "$dockerfile" >/dev/null
grep -F "/output" "$dockerfile" >/dev/null

echo "Codex strace Dockerfile static test passed."
