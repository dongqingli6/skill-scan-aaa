#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUESTED_PROJECT_DIR="${1:-}"
HOST="${SUB_MEMORY_WEB_HOST:-127.0.0.1}"
PORT="${SUB_MEMORY_WEB_PORT:-8765}"
BASE_DIR="${SUB_MEMORY_BASE_DIR:-$HOME/.codex/sub-memory}"

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
WEB_BIN="$PROJECT_DIR/.venv/bin/sub-memory-web"

if [[ ! -x "$WEB_BIN" ]]; then
  echo "sub-memory-web not found at $WEB_BIN" >&2
  echo "Run bootstrap first: $PROJECT_DIR/skills/sub-memory-bootstrap/scripts/bootstrap_local.sh $PROJECT_DIR" >&2
  exit 1
fi

mkdir -p "$BASE_DIR"

cat <<EOF
Starting sub-memory web UI.

Project: $PROJECT_DIR
sub-memory base dir: $BASE_DIR
URL: http://$HOST:$PORT/ui

Open that URL directly in your browser after the server starts.
Press Ctrl+C to stop.
EOF

exec "$WEB_BIN" --base-dir "$BASE_DIR" --host "$HOST" --port "$PORT"
