#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  code/platforms/codex/enforcer/realtime_monitor.py \
  code/platforms/codex/enforcer/violation_monitor.py \
  code/platforms/codex/sandbox/strace_parser.py

python3 - <<'PY'
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path("code").resolve()))

from platforms.codex.enforcer.realtime_monitor import PollingMonitor
from platforms.codex.enforcer.violation_monitor import monitor_existing_evidence
from platforms.codex.sandbox.strace_parser import parse_strace_log


OUTPUT_DIR = Path("analysis_results/codex_runtime_enforcement/runtime_kill_path_synthetic").resolve()
IMAGE = "ubuntu:24.04"
CONTAINER_NAME = f"codex-kill-path-synthetic-{uuid.uuid4().hex[:12]}"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_docker_env() -> dict[str, str]:
    docker_home = OUTPUT_DIR / "docker_client_home"
    docker_config = docker_home / ".docker"
    docker_config.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(docker_home),
        "DOCKER_CONFIG": str(docker_config),
    }


def docker_run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=safe_docker_env(),
        check=check,
    )


def assert_restricted_docker_command(command: list[str]) -> None:
    preview = " ".join(command)
    forbidden = ("--privileged", "--network host", "/var/run/docker.sock", "sudo docker")
    found = [item for item in forbidden if item in preview]
    assert not found, found
    assert "--network" in command and "none" in command, command
    assert "--read-only" in command, command
    assert "--cap-drop" in command and "ALL" in command, command
    assert "--security-opt" in command and "no-new-privileges" in command, command


def container_exists() -> bool:
    result = docker_run(
        ["docker", "ps", "-a", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
        check=False,
    )
    return CONTAINER_NAME in result.stdout.splitlines()


def cleanup_container() -> None:
    if not container_exists():
        return
    docker_run(["docker", "kill", CONTAINER_NAME], check=False)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not container_exists():
            return
        time.sleep(0.2)


if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True)

docker_run(["docker", "ps"])
image_check = docker_run(["docker", "image", "inspect", IMAGE], check=False)
if image_check.returncode != 0:
    raise RuntimeError(f"required local image is missing: {IMAGE}")

docker_command = [
    "docker",
    "run",
    "-d",
    "--rm",
    "--name",
    CONTAINER_NAME,
    "--network",
    "none",
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--pids-limit",
    "64",
    "--memory",
    "128m",
    "--cpus",
    "0.5",
    "--tmpfs",
    "/tmp:rw,nosuid,nodev",
    "-v",
    f"{OUTPUT_DIR}:/output:rw",
    IMAGE,
    "sleep",
    "60",
]
assert_restricted_docker_command(docker_command)
write_json(
    OUTPUT_DIR / "docker_command_preview.json",
    {
        "container_name": CONTAINER_NAME,
        "command": docker_command,
        "command_preview": " ".join(docker_command),
        "no_real_skill": True,
        "codex_executed": False,
        "strace_executed": False,
        "malicious_samples_executed": False,
    },
)

container_killed_by_monitor = False
kill_events: list[dict] = []


def on_violation(event: dict) -> None:
    global container_killed_by_monitor
    container_killed_by_monitor = True
    kill_result = docker_run(["docker", "kill", CONTAINER_NAME], check=False)
    kill_events.append(
        {
            "event": event,
            "docker_kill_returncode": kill_result.returncode,
            "docker_kill_stdout": kill_result.stdout.strip(),
            "docker_kill_stderr": kill_result.stderr.strip(),
        }
    )


monitor = PollingMonitor(
    output_dir=OUTPUT_DIR,
    event_log=OUTPUT_DIR / "violation_event.jsonl",
    kill_callback=on_violation,
    interval_seconds=0.1,
)

try:
    monitor.start()
    start_result = docker_run(docker_command)
    (OUTPUT_DIR / "docker_run_stdout.txt").write_text(start_result.stdout, encoding="utf-8")
    (OUTPUT_DIR / "docker_run_stderr.txt").write_text(start_result.stderr, encoding="utf-8")

    inspect = docker_run(
        ["docker", "inspect", CONTAINER_NAME, "--format", "{{.State.Running}}"],
        check=False,
    )
    assert inspect.stdout.strip() == "true", inspect

    synthetic_strace = OUTPUT_DIR / "strace.log.999"
    synthetic_strace.write_text(
        "\n".join(
            [
                'openat(AT_FDCWD, "/workspace/safe_skill/SKILL.md", O_WRONLY|O_TRUNC|O_CLOEXEC) = 3',
                'openat(AT_FDCWD, "/opt/codex-bundle/bin/codex", O_WRONLY|O_TRUNC|O_CLOEXEC) = 4',
                "",
            ]
        ),
        encoding="utf-8",
    )

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not container_killed_by_monitor:
        time.sleep(0.1)
finally:
    monitor.stop()
    cleanup_container()

deadline = time.monotonic() + 10
while time.monotonic() < deadline:
    if not container_exists():
        break
    time.sleep(0.2)

container_removed = not container_exists()
strace_result = parse_strace_log(OUTPUT_DIR, network_disabled=True)
write_json(OUTPUT_DIR / "strace_parse_result.json", strace_result)
write_json(
    OUTPUT_DIR / "dynamic_runtime_evidence.json",
    {
        "docker_network_mode": "none",
        "dynamic_execution_performed": True,
        "synthetic_kill_path_validation": True,
        "codex_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "malicious_samples_executed": False,
        "real_tokens_present": False,
    },
)
write_json(
    OUTPUT_DIR / "filesystem_diff.json",
    {
        "summary": {},
        "risks": [],
    },
)
write_json(
    OUTPUT_DIR / "network_disabled_verification.json",
    {
        "verification_type": "synthetic_runtime_kill_path",
        "network_mode_expected": "none",
        "external_api_attempt_observed": False,
        "external_api_blocked": True,
        "verification_status": "passed",
    },
)

violation_report = monitor_existing_evidence(
    dynamic_evidence_path=OUTPUT_DIR / "dynamic_runtime_evidence.json",
    strace_path=OUTPUT_DIR / "strace_parse_result.json",
    filesystem_diff_path=OUTPUT_DIR / "filesystem_diff.json",
    network_path=OUTPUT_DIR / "network_disabled_verification.json",
)
violation_report.update(
    {
        "monitor_mode": "synthetic_runtime_kill_path",
        "container_name": CONTAINER_NAME,
        "container_started": True,
        "container_killed_by_monitor": container_killed_by_monitor,
        "container_removed": container_removed,
        "kill_events": kill_events,
        "codex_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "malicious_samples_executed": False,
    }
)
write_json(OUTPUT_DIR / "violation_report.json", violation_report)

events_path = OUTPUT_DIR / "violation_event.jsonl"
events = [
    json.loads(line)
    for line in events_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
severities = {event["severity"] for event in events}

assert container_killed_by_monitor is True, violation_report
assert container_removed is True, violation_report
assert "HIGH" in severities, events
assert "CRITICAL" in severities, events
assert violation_report["container_killed_by_monitor"] is True, violation_report
assert violation_report["container_removed"] is True, violation_report
assert violation_report["risk_summary"]["HIGH"] >= 1, violation_report["risk_summary"]
assert violation_report["risk_summary"]["CRITICAL"] >= 1, violation_report["risk_summary"]

print(json.dumps(
    {
        "output_dir": str(OUTPUT_DIR),
        "container_killed_by_monitor": container_killed_by_monitor,
        "container_removed": container_removed,
        "event_count": len(events),
        "risk_summary": violation_report["risk_summary"],
    },
    indent=2,
))
PY

echo "Codex runtime kill-path synthetic integration test passed."
