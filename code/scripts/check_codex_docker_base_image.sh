#!/usr/bin/env bash
set -euo pipefail

DOCKER_CMD="${DOCKER_CMD:-docker}"
read -r -a docker_cmd_parts <<< "$DOCKER_CMD"
[ "${#docker_cmd_parts[@]}" -gt 0 ] || { echo "DOCKER_CMD is empty" >&2; exit 2; }

if "${docker_cmd_parts[@]}" image inspect ubuntu:24.04 >/dev/null 2>&1; then
  echo "Base image ubuntu:24.04 is present locally."
  exit 0
fi

echo "Base image ubuntu:24.04 is not present locally. Building may try to pull from network."
exit 1
