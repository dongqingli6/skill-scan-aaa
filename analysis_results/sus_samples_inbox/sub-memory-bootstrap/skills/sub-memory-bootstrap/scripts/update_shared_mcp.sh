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

cd "$PROJECT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing $PROJECT_DIR/.venv/bin/python" >&2
  echo "Run install_shared_mcp.sh first." >&2
  exit 1
fi

".venv/bin/python" -m pip install -r requirements.txt
".venv/bin/python" -m pip install -e .
".venv/bin/python" "$SCRIPT_DIR/configure_codex_project.py" --project-dir "$PROJECT_DIR"
bash "$SCRIPT_DIR/manage_mcp_daemon.sh" restart "$PROJECT_DIR"

cat <<EOF

Shared MCP update flow complete.

Next:
  Restart Codex if you updated the installed skill files in CODEX_HOME.
  Start a new Codex session from: $PROJECT_DIR
EOF
