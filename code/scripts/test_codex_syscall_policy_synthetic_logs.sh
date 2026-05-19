#!/usr/bin/env bash
set -euo pipefail

tmp=/tmp/codex_syscall_policy_synthetic_logs
rm -rf "$tmp"
mkdir -p "$tmp"

python3 - <<'PY'
from pathlib import Path

tmp = Path("/tmp/codex_syscall_policy_synthetic_logs")
(tmp / "strace.log.001").write_text(
    'openat(AT_FDCWD, "/home/empty/.ssh/id_rsa", O_RDONLY|O_CLOEXEC) = 3\n'
    'openat(AT_FDCWD, "/home/empty/.codex/config.toml", O_RDONLY|O_CLOEXEC) = 3\n'
    'openat(AT_FDCWD, "/home/empty/.agents/AGENTS.md", O_RDONLY|O_CLOEXEC) = 3\n'
    'openat(AT_FDCWD, "/tmp/project/.env", O_RDONLY|O_CLOEXEC) = 3\n',
    encoding="utf-8",
)
(tmp / "strace.log.002").write_text(
    'openat(AT_FDCWD, "/var/run/docker.sock", O_RDWR|O_CLOEXEC) = 4\n'
    'openat(AT_FDCWD, "/output/report.md", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666) = 5\n'
    'openat(AT_FDCWD, "/workspace/safe_skill/SKILL.md", O_RDONLY|O_CLOEXEC) = 6\n'
    'openat(AT_FDCWD, "/opt/codex-bundle/bin/codex", O_RDONLY|O_CLOEXEC) = 7\n',
    encoding="utf-8",
)
(tmp / "strace.log.003").write_text(
    'connect(8, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("203.0.113.10")}, 16) = -1 ENETUNREACH (Network is unreachable) /* api.openai.com */\n'
    'mount("tmpfs", "/mnt", "tmpfs", 0, NULL) = -1 EPERM (Operation not permitted)\n'
    'ptrace(PTRACE_TRACEME) = -1 EPERM (Operation not permitted)\n'
    'bpf(BPF_MAP_CREATE, 0x7fff, 120) = -1 EPERM (Operation not permitted)\n'
    'perf_event_open(0x7fff, 0, -1, -1, 0) = -1 EPERM (Operation not permitted)\n'
    'keyctl(KEYCTL_READ, 0, 0, 0, 0) = -1 EPERM (Operation not permitted)\n'
    'init_module(0x7fff, 10, "") = -1 EPERM (Operation not permitted)\n',
    encoding="utf-8",
)
PY

python3 code/platforms/codex/sandbox/strace_parser.py \
  --input "$tmp" \
  --output "$tmp/strace_parse_result.json" >/tmp/codex_syscall_policy_synthetic_parse.out

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

result = json.loads(Path("/tmp/codex_syscall_policy_synthetic_logs/strace_parse_result.json").read_text(encoding="utf-8"))
findings = result["findings"]

def by_rule(rule: str) -> list[dict]:
    return [item for item in findings if item.get("matched_rule") == rule]

assert result["parsed_file_count"] == 3, result["input_files"]
assert result["syscall_policy"]["exists"] is True, result["syscall_policy"]
assert result["syscall_policy"]["valid"] is True, result["syscall_policy"]

assert by_rule("sensitive_ssh_read")[0]["severity"] in {"HIGH", "CRITICAL"}
assert by_rule("sensitive_codex_home_read")[0]["severity"] in {"HIGH", "CRITICAL"}
assert by_rule("sensitive_agents_home_read")[0]["severity"] in {"HIGH", "CRITICAL"}
assert by_rule("dotenv_read")[0]["severity"] in {"HIGH", "CRITICAL"}
assert by_rule("docker_socket_access")[0]["severity"] == "CRITICAL"
assert by_rule("output_write")[0]["severity"] == "LOW"
assert by_rule("safe_skill_read")[0]["severity"] == "LOW"
assert by_rule("codex_bundle_read")[0]["severity"] == "LOW"
assert by_rule("blocked_openai_network_none")[0]["severity"] == "LOW"
assert by_rule("namespace_mount")[0]["severity"] == "CRITICAL"
assert by_rule("ptrace_use")[0]["severity"] == "CRITICAL"
assert by_rule("bpf_use")[0]["severity"] == "CRITICAL"
assert by_rule("perf_event_open_use")[0]["severity"] in {"HIGH", "CRITICAL"}
assert by_rule("kernel_keyring_use")[0]["severity"] in {"HIGH", "CRITICAL"}
assert by_rule("module_loading")[0]["severity"] == "CRITICAL"

summary = result["syscall_policy_summary"]
assert summary["risk_summary"]["LOW"] >= 3, summary
assert summary["risk_summary"]["HIGH"] >= 1, summary
assert summary["risk_summary"]["CRITICAL"] >= 4, summary
assert result["high_risk_syscalls"], result
assert result["critical_risk_syscalls"], result
assert "docker_socket_access" in result["matched_policy_rules"], result["matched_policy_rules"]

script_text = Path("code/scripts/test_codex_syscall_policy_synthetic_logs.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec"]:
    assert forbidden not in script_text, f"synthetic test must not run {forbidden}"

print("Codex syscall policy synthetic logs test passed.")
PY

echo "Codex syscall policy synthetic logs test passed."
