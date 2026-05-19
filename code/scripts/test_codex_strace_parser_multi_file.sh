#!/usr/bin/env bash
set -euo pipefail

tmp=/tmp/codex_strace_parser_test
mkdir -p "$tmp"

python3 - <<'PY'
from pathlib import Path

tmp = Path("/tmp/codex_strace_parser_test")
(tmp / "strace.log.101").write_text(
    'execve("/opt/codex-bundle/bin/codex", ["codex", "exec"], 0xabc /* 10 vars */) = 0\n'
    'openat(AT_FDCWD, "/home/codexsafe/.codex/config.toml", O_RDONLY|O_CLOEXEC) = 3\n',
    encoding="utf-8",
)
(tmp / "strace.log.102").write_text(
    'openat(AT_FDCWD, "/workspace/safe_skill/SKILL.md", O_RDONLY|O_CLOEXEC) = 3\n'
    'socket(AF_INET, SOCK_STREAM, IPPROTO_IP) = 4\n'
    'connect(4, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("203.0.113.10")}, 16) = -1 ENETUNREACH (Network is unreachable)\n',
    encoding="utf-8",
)
(tmp / "strace.log.103").write_text(
    'openat(AT_FDCWD, "/output/codex_docker_smoke_stderr.txt", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666) = 5\n',
    encoding="utf-8",
)
PY

python3 code/platforms/codex/sandbox/strace_parser.py \
  --input "$tmp" \
  --output "$tmp/strace_parse_result.json" >/tmp/codex_strace_parser_test.out

python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path("/tmp/codex_strace_parser_test/strace_parse_result.json").read_text(encoding="utf-8"))
assert result["parsed_file_count"] >= 3, result["parsed_file_count"]
counts = result["summary_counts"]
for name in ["execve", "openat", "socket", "connect"]:
    assert counts[name] > 0, (name, counts)

findings = result["findings"]
high_or_critical = [f for f in findings if f["severity"] in {"HIGH", "CRITICAL"}]
assert not any("/home/codexsafe/.codex" in f.get("line", "") for f in high_or_critical), high_or_critical
assert not any("/output/codex_docker_smoke_stderr.txt" in f.get("line", "") for f in high_or_critical), high_or_critical
assert result["risk_summary"]["HIGH"] == 0, result["risk_summary"]
assert result["risk_summary"]["CRITICAL"] == 0, result["risk_summary"]
PY

echo "Codex strace parser multi-file test passed."
