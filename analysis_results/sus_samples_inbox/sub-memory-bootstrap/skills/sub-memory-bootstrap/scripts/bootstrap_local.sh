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

"$PYTHON_BIN" -m venv .venv
".venv/bin/python" -m pip install -r requirements.txt
".venv/bin/python" -m pip install -e .

if [[ -f ".env.example" && ! -f ".env" ]]; then
  cp .env.example .env
fi

".venv/bin/python" "$SCRIPT_DIR/configure_codex_project.py" \
  --project-dir "$PROJECT_DIR"
"$SCRIPT_DIR/manage_mcp_daemon.sh" restart "$PROJECT_DIR"

BASE_DIR="${SUB_MEMORY_BASE_DIR:-$HOME/.codex/sub-memory}"
MCP_HOST="${SUB_MEMORY_MCP_HOST:-127.0.0.1}"
MCP_PORT="${SUB_MEMORY_MCP_PORT:-8766}"
MCP_PATH="${SUB_MEMORY_MCP_PATH:-/mcp}"

if [[ "$MCP_PATH" != /* ]]; then
  MCP_PATH="/$MCP_PATH"
fi

cat <<EOF
Bootstrap complete.

Project: $PROJECT_DIR
sub-memory base dir: $BASE_DIR
Agent entrypoint: $PROJECT_DIR/.venv/bin/sub-memory-agent
MCP entrypoint: $PROJECT_DIR/.venv/bin/sub-memory-mcp
Shared MCP daemon: $PROJECT_DIR/skills/sub-memory-bootstrap/scripts/manage_mcp_daemon.sh
Shared MCP URL: http://$MCP_HOST:$MCP_PORT$MCP_PATH
Web entrypoint: $PROJECT_DIR/.venv/bin/sub-memory-web
Codex project config: $PROJECT_DIR/.codex/config.toml
AGENTS rules: $PROJECT_DIR/AGENTS.md

Next recommended checks:
  $PROJECT_DIR/.venv/bin/sub-memory-agent --help
  $PROJECT_DIR/.venv/bin/sub-memory-mcp --help
  $PROJECT_DIR/skills/sub-memory-bootstrap/scripts/manage_mcp_daemon.sh status $PROJECT_DIR
  $PROJECT_DIR/.venv/bin/sub-memory-web --help
  $PROJECT_DIR/.venv/bin/python -m unittest discover -s tests
  Start a new Codex session from $PROJECT_DIR
  Optional web UI: $PROJECT_DIR/skills/sub-memory-bootstrap/scripts/start_web_ui.sh $PROJECT_DIR
EOF
