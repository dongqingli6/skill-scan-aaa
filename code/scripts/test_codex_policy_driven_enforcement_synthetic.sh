#!/usr/bin/env bash
set -euo pipefail

tmp=/tmp/codex_policy_driven_enforcement_synthetic
rm -rf "$tmp"
mkdir -p "$tmp"

python3 - <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("code").resolve()))

from platforms.codex.enforcer.enforcement_report import build_report, write_report
from platforms.codex.enforcer.realtime_monitor import PollingMonitor
from platforms.codex.sandbox.strace_parser import parse_strace_log

output_dir = Path("/tmp/codex_policy_driven_enforcement_synthetic")
container_name = "codex-policy-driven-fake-container"
event_log = output_dir / "violation_event.jsonl"
violation_report_path = output_dir / "violation_report.json"
trace_file = output_dir / "strace.log"

trace_file.write_text(
    'openat(AT_FDCWD, "/home/empty/.ssh/id_rsa", O_RDONLY) = 3\n'
    'openat(AT_FDCWD, "/var/run/docker.sock", O_RDWR) = 3\n',
    encoding="utf-8",
)

fake_kills: list[dict] = []

def fake_kill_callback(event: dict) -> None:
    fake_kills.append({"container_name": event.get("container_name"), "event": event})

runtime_response = {
    "on_high_violation": "kill_container",
    "on_critical_violation": "kill_container",
}
monitor = PollingMonitor(
    output_dir=output_dir,
    event_log=event_log,
    container_name=container_name,
    runtime_response=runtime_response,
    kill_on_high=True,
    kill_callback=fake_kill_callback,
    interval_seconds=0.01,
)
events = monitor.scan_once()
strace_result = parse_strace_log(output_dir, network_disabled=True)

risk_summary = strace_result["risk_summary"]
container_killed_by_monitor = bool(fake_kills)
violation_report = {
    "container_name": container_name,
    "container_started": False,
    "container_killed_by_monitor": container_killed_by_monitor,
    "container_removed": True,
    "fake_kill_called": bool(fake_kills),
    "fake_kill_container_name": fake_kills[0]["container_name"] if fake_kills else None,
    "runtime_response": runtime_response,
    "risk_summary": risk_summary,
    "violations": events,
    "matched_policy_rules": strace_result["matched_policy_rules"],
    "high_risk_syscalls": strace_result["high_risk_syscalls"],
    "critical_risk_syscalls": strace_result["critical_risk_syscalls"],
}
violation_report_path.write_text(json.dumps(violation_report, indent=2, ensure_ascii=False), encoding="utf-8")

report = build_report(
    skill_path="synthetic-policy-driven-log-only",
    output_dir=output_dir,
    command_info={"container_name": container_name},
    run_status=None,
    timeout_observed=False,
    monitor_events=events,
    container_started=False,
    container_killed_by_monitor=container_killed_by_monitor,
    container_removed=True,
    strace_result=strace_result,
    filesystem_diff={"summary": {}},
    violation_report=violation_report,
)
write_report(report, output_dir)

assert risk_summary["HIGH"] > 0 or risk_summary["CRITICAL"] > 0, risk_summary
assert strace_result["matched_policy_rules"], strace_result
assert any(event.get("enforcement_action") == "kill_container" for event in events), events
assert container_killed_by_monitor is True
assert bool(fake_kills) is True
assert fake_kills[0]["container_name"] == container_name, fake_kills
assert event_log.exists() and event_log.read_text(encoding="utf-8").strip(), event_log
assert violation_report_path.exists(), violation_report_path
assert report["container_killed_by_monitor"] is True, report
assert report["enforcement_action"] == "kill_container", report
assert report["matched_policy_rules"], report
assert report["critical_risk_syscalls"], report

print("Codex policy-driven enforcement synthetic test passed.")
PY

python3 - <<'PY'
from pathlib import Path

script_text = Path("code/scripts/test_codex_policy_driven_enforcement_synthetic.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec"]:
    assert forbidden not in script_text, f"synthetic test must not run {forbidden}"

print("Codex policy-driven enforcement synthetic guard passed.")
PY

echo "Codex policy-driven enforcement synthetic test passed."
