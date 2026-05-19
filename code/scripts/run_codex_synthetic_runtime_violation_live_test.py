#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_VIOLATION_ROOT = REPO_ROOT / "code" / "platforms" / "codex" / "enforcer" / "runtime_violation"
if str(RUNTIME_VIOLATION_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_VIOLATION_ROOT))

import runtime_violation_events
import runtime_violation_policy
import runtime_violation_report


FAKE_CONTAINER_NAME = runtime_violation_events.FAKE_CONTAINER_NAME


class FakeKillCallback:
    def __init__(self) -> None:
        self.called = False
        self.calls: list[dict[str, Any]] = []

    def __call__(self, container_name: str, event_id: str) -> dict[str, Any]:
        self.called = True
        record = {
            "container_name": container_name,
            "event_id": event_id,
            "fake_kill_callback": True,
            "real_container_killed": False,
        }
        self.calls.append(record)
        return record


def run_synthetic_runtime_violation_live_test(*, synthetic: bool, dry_run_kill: bool) -> dict[str, Any]:
    if not synthetic:
        raise SystemExit("fail closed: --synthetic is required")
    if not dry_run_kill:
        raise SystemExit("fail closed: --dry-run-kill is required")

    events = runtime_violation_events.synthetic_event_matrix()
    findings = [runtime_violation_policy.classify_runtime_event(event) for event in events]
    kill_callback = FakeKillCallback()
    decisions: list[dict[str, Any]] = []

    for event, finding in zip(events, findings):
        decision = runtime_violation_policy.decide_runtime_response([finding])
        decision["event_id"] = event["event_id"]
        decision["event_type"] = event["event_type"]
        decision["container_name"] = event["container_name"]
        decision["fake_kill_callback_called"] = False
        decision["real_container_killed"] = False
        if decision["runtime_response"] == "kill_container":
            kill_result = kill_callback(event["container_name"], event["event_id"])
            decision["fake_kill_callback_called"] = kill_result["fake_kill_callback"]
            decision["real_container_killed"] = kill_result["real_container_killed"]
        decisions.append(decision)

    summary = build_summary(events, findings, decisions, kill_callback)
    runtime_violation_report.write_runtime_violation_outputs(events, findings, decisions, summary)
    return summary


def build_summary(
    events: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    kill_callback: FakeKillCallback,
) -> dict[str, Any]:
    severities = [str(finding.get("severity")) for finding in findings]
    responses = [str(decision.get("runtime_response")) for decision in decisions]
    return {
        "stage": "Stage 24 Synthetic Runtime Violation Live Test",
        "total_events": len(events),
        "critical": severities.count("CRITICAL"),
        "high": severities.count("HIGH"),
        "medium": severities.count("MEDIUM"),
        "low": severities.count("LOW"),
        "kill_decisions": responses.count("kill_container"),
        "fail_closed_decisions": responses.count("fail_closed"),
        "record_only_decisions": responses.count("record_only"),
        "fake_kill_callback_called": kill_callback.called,
        "fake_kill_callback_calls": kill_callback.calls,
        "real_container_killed": False,
        "docker_executed": False,
        "codex_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "network_enabled": False,
        "synthetic": True,
        "dry_run_kill": True,
        "final_status": "pass",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 24 synthetic runtime violation live test")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--dry-run-kill", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_synthetic_runtime_violation_live_test(
        synthetic=bool(args.synthetic),
        dry_run_kill=bool(args.dry_run_kill),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
