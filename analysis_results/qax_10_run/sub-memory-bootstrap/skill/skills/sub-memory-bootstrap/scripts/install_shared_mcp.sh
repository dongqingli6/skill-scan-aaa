#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUESTED_PROJECT_DIR="${1:-}"

if command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="python3.11"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "python3.11 or python3 is required" >&2
  exit 1
fi

RESOLVE_ARGS=("$PYTHON_BIN" "$SCRIPT_DIR/ensure_repo_checkout.py")
if [[ -n "$REQUESTED_PROJECT_DIR" ]]; then
  RESOLVE_ARGS+=("--project-dir" "$REQUESTED_PROJECT_DIR")
fi

PROJECT_DIR="$("${RESOLVE_ARGS[@]}")"

"$SCRIPT_DIR/bootstrap_local.sh" "$PROJECT_DIR"

cat <<EOF

Shared MCP install flow complete.

Next:
  Restart Codex to pick up new skills if you installed or updated the skill itself.
  Start a new Codex session from: $PROJECT_DIR
EOF
