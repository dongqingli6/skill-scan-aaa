#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUESTED_PROJECT_DIR="${2:-}"
ACTION="${1:-start}"
HOST="${SUB_MEMORY_MCP_HOST:-127.0.0.1}"
PORT="${SUB_MEMORY_MCP_PORT:-8766}"
PATH_SUFFIX="${SUB_MEMORY_MCP_PATH:-/mcp}"
BASE_DIR="${SUB_MEMORY_BASE_DIR:-$HOME/.codex/sub-memory}"
PID_FILE="$BASE_DIR/sub-memory-mcp.pid"
LOG_FILE="$BASE_DIR/sub-memory-mcp.log"

if [[ "$PATH_SUFFIX" != /* ]]; then
  PATH_SUFFIX="/$PATH_SUFFIX"
fi

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
MCP_BIN="$PROJECT_DIR/.venv/bin/sub-memory-mcp"

if [[ ! -x "$MCP_BIN" ]]; then
  echo "sub-memory-mcp not found at $MCP_BIN" >&2
  echo "Run bootstrap first: $PROJECT_DIR/skills/sub-memory-bootstrap/scripts/bootstrap_local.sh $PROJECT_DIR" >&2
  exit 1
fi

mkdir -p "$BASE_DIR"

if [[ ! -f "$BASE_DIR/.env" ]]; then
  if [[ -f "$PROJECT_DIR/.env" ]]; then
    cp "$PROJECT_DIR/.env" "$BASE_DIR/.env"
  elif [[ -f "$PROJECT_DIR/.env.example" ]]; then
    cp "$PROJECT_DIR/.env.example" "$BASE_DIR/.env"
  fi
fi

mcp_url() {
  printf 'http://%s:%s%s' "$HOST" "$PORT" "$PATH_SUFFIX"
}

socket_ready() {
  "$PYTHON_BIN" - "$HOST" "$PORT" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket()
sock.settimeout(0.5)
try:
    sock.connect((host, port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
}

pid_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    tr -d '[:space:]' <"$PID_FILE"
  fi
}

write_pid() {
  local pid="$1"
  printf '%s\n' "$pid" >"$PID_FILE"
}

clear_pid() {
  rm -f "$PID_FILE"
}

wait_until_ready() {
  local attempts=240
  local sleep_seconds=0.25
  for _ in $(seq 1 "$attempts"); do
    if socket_ready; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  return 1
}

print_status() {
  local pid="${1:-}"
  cat <<EOF
Project: $PROJECT_DIR
sub-memory base dir: $BASE_DIR
MCP URL: $(mcp_url)
Log file: $LOG_FILE
PID file: $PID_FILE
PID: ${pid:-not running}
EOF
}

start_server() {
  local pid
  pid="$(read_pid || true)"
  if [[ -n "$pid" ]] && pid_running "$pid"; then
    echo "sub-memory MCP daemon is already running."
    print_status "$pid"
    return 0
  fi

  if socket_ready; then
    echo "Port $PORT is already accepting connections. Refusing to start a duplicate daemon." >&2
    print_status
    return 1
  fi

  nohup "$MCP_BIN" \
    --base-dir "$BASE_DIR" \
    --transport streamable-http \
    --host "$HOST" \
    --port "$PORT" \
    </dev/null >>"$LOG_FILE" 2>&1 &
  pid="$!"
  write_pid "$pid"

  if wait_until_ready; then
    echo "Started sub-memory MCP daemon."
    print_status "$pid"
    return 0
  fi

  if pid_running "$pid"; then
    kill "$pid" 2>/dev/null || true
  fi
  clear_pid
  echo "sub-memory MCP daemon failed to become ready." >&2
  print_status "$pid" >&2
  return 1
}

stop_server() {
  local pid
  pid="$(read_pid || true)"
  if [[ -z "$pid" ]]; then
    echo "sub-memory MCP daemon is not running."
    clear_pid
    return 0
  fi

  if pid_running "$pid"; then
    kill "$pid"
    for _ in $(seq 1 20); do
      if ! pid_running "$pid"; then
        break
      fi
      sleep 0.25
    done
  fi

  clear_pid
  echo "Stopped sub-memory MCP daemon."
}

status_server() {
  local pid
  pid="$(read_pid || true)"
  if [[ -n "$pid" ]] && pid_running "$pid"; then
    echo "sub-memory MCP daemon is running."
    print_status "$pid"
    return 0
  fi

  echo "sub-memory MCP daemon is not running."
  print_status
  return 1
}

case "$ACTION" in
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server || true
    start_server
    ;;
  status)
    status_server
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status} [project-dir]" >&2
    exit 1
    ;;
esac
