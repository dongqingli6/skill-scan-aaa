#!/usr/bin/env bash
set -euo pipefail

tmp=/tmp/codex_realtime_monitor_test
mkdir -p "$tmp"

python3 -m py_compile code/platforms/codex/enforcer/realtime_monitor.py

python3 - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path("code").resolve()))
from platforms.codex.enforcer.realtime_monitor import scan_text

benign = 'openat(AT_FDCWD, "/output/codex_docker_smoke_stderr.txt", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666) = 5\n'
events = scan_text(benign, source="/tmp/codex_realtime_monitor_test/strace.log")
assert not any(event["severity"] == "HIGH" for event in events), events
assert not any(event["severity"] == "CRITICAL" for event in events), events

ssh = 'openat(AT_FDCWD, "/home/empty/.ssh/id_rsa", O_RDONLY|O_CLOEXEC) = 3\n'
events = scan_text(ssh, source="/tmp/codex_realtime_monitor_test/strace.log")
assert any(event["severity"] in {"HIGH", "CRITICAL"} for event in events), events

safe_write = 'openat(AT_FDCWD, "/workspace/safe_skill/SKILL.md", O_WRONLY|O_TRUNC|O_CLOEXEC) = 3\n'
events = scan_text(safe_write, source="/tmp/codex_realtime_monitor_test/strace.log")
assert any(event["severity"] == "HIGH" for event in events), events

bundle_write = 'openat(AT_FDCWD, "/opt/codex-bundle/bin/codex", O_WRONLY|O_TRUNC|O_CLOEXEC) = 3\n'
events = scan_text(bundle_write, source="/tmp/codex_realtime_monitor_test/strace.log")
assert any(event["severity"] == "CRITICAL" for event in events), events
PY

echo "Codex realtime monitor synthetic violation test passed."
