#!/usr/bin/env bash
set -euo pipefail

bash -n code/scripts/run_codex_docker_safe_smoke_MANUAL.sh
bash -n code/scripts/check_codex_docker_base_image.sh
bash -n code/scripts/test_codex_docker_manual_fail_closed.sh
bash -n code/scripts/audit_codex_docker_manual_script.sh

dockerfile="code/platforms/codex/sandbox/docker/Dockerfile.codex-sandbox"

grep -Eq '^[[:space:]]*FROM[[:space:]]+ubuntu:24\.04' "$dockerfile"

if grep -E -n -- 'useradd|adduser|apt install|curl|wget|npm install|pip install|codex exec' "$dockerfile"; then
  echo "Forbidden pattern found in Dockerfile.codex-sandbox" >&2
  exit 1
fi

grep -F 'USER 1000:1000' "$dockerfile" >/dev/null
grep -F '/opt/codex-bundle/bin' "$dockerfile" >/dev/null
grep -F 'CODEX_HOME=/home/codexsafe/.codex' "$dockerfile" >/dev/null
grep -F '/workspace' "$dockerfile" >/dev/null
grep -F '/output' "$dockerfile" >/dev/null

set +e
bash code/scripts/check_codex_docker_base_image.sh
status=$?
set -e
if [ "$status" -ne 0 ]; then
  echo "Base image check reported missing local image; no pull was attempted."
fi

echo "Dockerfile static test passed."
