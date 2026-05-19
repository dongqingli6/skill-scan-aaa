"""Entrypoint for Codex runtime enforcement harness."""

from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.enforcer.docker_command_builder import build_docker_command_preview
    from platforms.codex.enforcer.enforcement_report import build_report, write_report
    from platforms.codex.enforcer.realtime_monitor import PollingMonitor
    from platforms.codex.enforcer.runtime_executor import (
        build_enforced_docker_run_command,
        check_docker_access,
        check_sensitive_env_absent,
        collect_logs,
        confirm_no_container_remains,
        kill_container,
        start_container,
        wait_with_timeout,
    )
    from platforms.codex.enforcer.runtime_policy import DEFAULT_POLICY, load_policy, validate_skill_path
    from platforms.codex.enforcer.violation_monitor import monitor_existing_evidence
    from platforms.codex.sandbox.filesystem_diff import diff_snapshots
    from platforms.codex.sandbox.filesystem_snapshot import write_snapshot
    from platforms.codex.sandbox.strace_parser import parse_strace_log
else:  # pragma: no cover
    from .docker_command_builder import build_docker_command_preview
    from .enforcement_report import build_report, write_report
    from .realtime_monitor import PollingMonitor
    from .runtime_executor import (
        build_enforced_docker_run_command,
        check_docker_access,
        check_sensitive_env_absent,
        collect_logs,
        confirm_no_container_remains,
        kill_container,
        start_container,
        wait_with_timeout,
    )
    from .runtime_policy import DEFAULT_POLICY, load_policy, validate_skill_path
    from .violation_monitor import monitor_existing_evidence
    from ..sandbox.filesystem_diff import diff_snapshots
    from ..sandbox.filesystem_snapshot import write_snapshot
    from ..sandbox.strace_parser import parse_strace_log


def build_plan(args: argparse.Namespace) -> dict:
    policy = load_policy(args.policy)
    decision = validate_skill_path(policy, args.skill_path)
    command_preview = None
    if decision.allowed:
        command_preview = build_docker_command_preview(
            policy=policy,
            skill_path=args.skill_path,
            output_dir=args.output_dir,
            codex_bundle_ro=args.codex_bundle_ro,
            seccomp_profile=args.seccomp_profile,
            apparmor_profile=args.apparmor_profile,
            egress_policy=args.egress_policy,
            network_mode=args.network_mode,
        )
    return {
        "mode": args.mode,
        "dynamic_evidence_path": args.dynamic_evidence_path,
        "policy_decision": decision.__dict__,
        "docker_command_preview": command_preview,
        "expected_mounts": command_preview.get("expected_mounts") if command_preview else None,
        "expected_network_policy": command_preview.get("expected_network_policy") if command_preview else policy.get("network_policy", {}),
        "expected_enforcement_response": policy.get("runtime_response", {}),
        "enforce_todo": "enforce mode will start a monitored container and kill it on HIGH/CRITICAL violations",
        "dynamic_execution_performed": False,
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _clear_previous_enforce_outputs(output_dir: Path) -> None:
    names = [
        "before_snapshot.json",
        "after_snapshot.json",
        "container_logs.json",
        "docker_command_preview.json",
        "docker_run_stderr.txt",
        "docker_run_stdout.txt",
        "dynamic_runtime_evidence.json",
        "filesystem_diff.json",
        "network_disabled_verification.json",
        "report.md",
        "runtime_enforcement_report.json",
        "strace_parse_result.json",
        "violation_event.jsonl",
        "violation_report.json",
    ]
    for name in names:
        path = output_dir / name
        if path.exists() and path.is_file():
            path.unlink()
    for path in output_dir.glob("strace.log*"):
        if path.is_file():
            path.unlink()


def _network_verification_from_stderr(output_dir: Path) -> dict:
    stderr_path = output_dir / "docker_run_stderr.txt"
    lines = stderr_path.read_text(encoding="utf-8", errors="replace").splitlines() if stderr_path.exists() else []
    evidence = [
        line
        for line in lines
        if "api.openai.com" in line
        or "failed to connect to websocket" in line
        or "failed to lookup address information" in line
    ]
    return {
        "verification_type": "runtime_enforcement_network_disabled",
        "network_mode_expected": "none",
        "external_api_attempt_observed": bool(evidence),
        "external_api_blocked": bool(evidence),
        "verification_status": "passed" if evidence else "inconclusive",
        "evidence_lines": evidence[:20],
    }


def run_enforce(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_previous_enforce_outputs(output_dir)
    policy = load_policy(args.policy)
    decision = validate_skill_path(policy, args.skill_path)
    if not decision.allowed:
        raise RuntimeError(decision.reason)
    if Path(args.skill_path).name != "safe_skill":
        raise RuntimeError("enforce mode is restricted to safe_skill")
    check_sensitive_env_absent()
    check_docker_access(args.docker_cmd)

    before_snapshot = output_dir / "before_snapshot.json"
    after_snapshot = output_dir / "after_snapshot.json"
    write_snapshot(output_dir, before_snapshot, "before_enforce")

    command_info = build_enforced_docker_run_command(
        policy=policy,
        skill_path=args.skill_path,
        output_dir=output_dir,
        codex_bundle_ro=args.codex_bundle_ro,
        image=args.image,
        timeout_seconds=args.timeout_seconds,
        docker_cmd=args.docker_cmd,
    )
    _write_json(output_dir / "docker_command_preview.json", command_info)

    container_killed_by_monitor = False
    kill_events: list[dict] = []
    runtime_response = policy.get("runtime_response", {})
    kill_on_high = (
        runtime_response.get("on_high_violation") == "kill_container"
        and runtime_response.get("on_critical_violation") == "kill_container"
    )

    def on_violation(event: dict) -> None:
        nonlocal container_killed_by_monitor
        result = kill_container(args.docker_cmd, command_info["container_name"], output_dir)
        container_killed_by_monitor = True
        kill_events.append({"event": event, "docker_kill": result})

    monitor = PollingMonitor(
        output_dir=output_dir,
        event_log=output_dir / "violation_event.jsonl",
        container_name=command_info["container_name"],
        runtime_response=runtime_response,
        kill_on_high=kill_on_high,
        kill_callback=on_violation,
        interval_seconds=1.0,
    )
    process = None
    run_status = None
    timeout_observed = False
    container_started = False
    try:
        monitor.start()
        process = start_container(command_info["command"], output_dir)
        container_started = True
        run_status, outer_timeout = wait_with_timeout(process, args.timeout_seconds)
        timeout_observed = bool(outer_timeout or run_status == 124)
        if outer_timeout:
            kill_container(args.docker_cmd, command_info["container_name"], output_dir)
    finally:
        monitor.stop()
        if process and process.poll() is None:
            kill_container(args.docker_cmd, command_info["container_name"], output_dir)
            process.wait(timeout=10)
        if monitor.kill_error:
            raise RuntimeError(f"runtime monitor kill failed: {monitor.kill_error}")

    time.sleep(1)
    container_removed = confirm_no_container_remains(args.docker_cmd, command_info["container_name"], output_dir)
    logs = collect_logs(output_dir)
    _write_json(output_dir / "container_logs.json", logs)

    strace_result = parse_strace_log(output_dir, network_disabled=True)
    _write_json(output_dir / "strace_parse_result.json", strace_result)

    write_snapshot(output_dir, after_snapshot, "after_enforce")
    fs_diff = diff_snapshots(before_snapshot, after_snapshot)
    _write_json(output_dir / "filesystem_diff.json", fs_diff)

    network = _network_verification_from_stderr(output_dir)
    _write_json(output_dir / "network_disabled_verification.json", network)
    dynamic_runtime = {
        "docker_network_mode": "none",
        "dynamic_execution_performed": True,
        "malicious_samples_executed": False,
        "real_tokens_present": False,
    }
    _write_json(output_dir / "dynamic_runtime_evidence.json", dynamic_runtime)

    violation_report = monitor_existing_evidence(
        dynamic_evidence_path=output_dir / "dynamic_runtime_evidence.json",
        strace_path=output_dir / "strace_parse_result.json",
        filesystem_diff_path=output_dir / "filesystem_diff.json",
        network_path=output_dir / "network_disabled_verification.json",
    )
    violation_report.update(
        {
            "container_name": command_info["container_name"],
            "container_started": container_started,
            "container_killed_by_monitor": container_killed_by_monitor,
            "container_removed": container_removed,
            "kill_events": kill_events,
            "runtime_response": runtime_response,
        }
    )
    _write_json(output_dir / "violation_report.json", violation_report)

    report = build_report(
        skill_path=str(Path(args.skill_path).resolve()),
        output_dir=output_dir,
        command_info=command_info,
        run_status=run_status,
        timeout_observed=timeout_observed,
        monitor_events=monitor.events,
        container_started=container_started,
        container_killed_by_monitor=container_killed_by_monitor,
        container_removed=container_removed,
        strace_result=strace_result,
        filesystem_diff=fs_diff,
        violation_report=violation_report,
    )
    write_report(report, output_dir)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex runtime enforcement harness")
    parser.add_argument("--skill-path", required=True)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--codex-bundle-ro", required=True)
    parser.add_argument("--seccomp-profile")
    parser.add_argument("--apparmor-profile")
    parser.add_argument("--egress-policy")
    parser.add_argument("--network-mode", choices=["none", "controlled"], default="none")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=["plan-only", "enforce"], default="plan-only")
    parser.add_argument("--dynamic-evidence-path", default="analysis_results/codex_dynamic_security_report/dynamic_security_report.json")
    parser.add_argument("--image", default="codex-safe-smoke:strace")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--docker-cmd", default="docker")
    parser.add_argument("--plan-output")
    args = parser.parse_args()

    if args.mode == "enforce":
        if args.seccomp_profile or args.apparmor_profile or args.egress_policy or args.network_mode != "none":
            print("fail-closed: seccomp/AppArmor/egress hardening options are currently plan-only", file=sys.stderr)
            return 2
        try:
            report = run_enforce(args)
        except Exception as exc:
            print(f"fail-closed: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if not (report["risk_summary"]["HIGH"] or report["risk_summary"]["CRITICAL"]) else 3

    plan = build_plan(args)
    text = json.dumps(plan, indent=2, ensure_ascii=False)
    if args.plan_output:
        out = Path(args.plan_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if plan["policy_decision"]["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
