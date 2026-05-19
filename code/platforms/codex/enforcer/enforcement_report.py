"""Runtime enforcement report writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def summarize_risks(*risk_sources: dict[str, Any]) -> dict[str, int]:
    summary = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for source in risk_sources:
        for severity in summary:
            summary[severity] += int(source.get(severity, 0))
    return summary


def build_report(
    *,
    skill_path: str,
    output_dir: str | Path,
    command_info: dict[str, Any],
    run_status: int | None,
    timeout_observed: bool,
    monitor_events: list[dict],
    container_started: bool,
    container_killed_by_monitor: bool,
    container_removed: bool,
    strace_result: dict[str, Any],
    filesystem_diff: dict[str, Any],
    violation_report: dict[str, Any],
) -> dict[str, Any]:
    strace_risk = strace_result.get("risk_summary", {})
    violation_risk = {
        key: value
        for key, value in violation_report.get("risk_summary", {}).items()
        if key in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    }
    risk_summary = summarize_risks(strace_risk, violation_risk)
    final_verdict = (
        "safe_skill-only runtime enforcement completed; no HIGH/CRITICAL violation observed; "
        "Codex network attempts were blocked by Docker --network none."
    )
    if risk_summary["HIGH"] or risk_summary["CRITICAL"]:
        final_verdict = "runtime enforcement observed HIGH/CRITICAL violation and should kill or fail closed."
    elif not timeout_observed and run_status not in {0, 124}:
        final_verdict = (
            "safe_skill-only runtime enforcement started and no HIGH/CRITICAL violation was observed, "
            "but the run ended before the expected no-network timeout; inspect stderr for runtime setup errors."
        )
    violations = monitor_events + violation_report.get("violations", [])
    enforcement_actions = [
        item.get("enforcement_action") or item.get("recommended_action")
        for item in violations
        if item.get("enforcement_action") or item.get("recommended_action")
    ]
    enforcement_action = "kill_container" if "kill_container" in enforcement_actions else (enforcement_actions[0] if enforcement_actions else None)
    syscall_policy_summary = strace_result.get("syscall_policy_summary", {})
    high_risk_syscalls = strace_result.get("high_risk_syscalls", [])
    critical_risk_syscalls = strace_result.get("critical_risk_syscalls", [])
    matched_policy_rules = strace_result.get("matched_policy_rules", {})

    return {
        "target_platform": "codex",
        "skill_path": skill_path,
        "mode": "enforce",
        "docker_network_mode": "none",
        "sample_mount": "read-only",
        "output_mount": "writable",
        "codex_bundle_mount": "read-only",
        "real_tokens_present": False,
        "malicious_samples_executed": False,
        "container_name": command_info.get("container_name"),
        "container_started": container_started,
        "container_killed_by_monitor": container_killed_by_monitor,
        "container_removed": container_removed,
        "run_status": run_status,
        "timeout_observed": timeout_observed,
        "expected_network_block": True,
        "violations": violations,
        "enforcement_action": enforcement_action,
        "enforcement_actions": enforcement_actions,
        "runtime_response": violation_report.get("runtime_response", {}),
        "syscall_policy_summary": syscall_policy_summary,
        "high_risk_syscalls": high_risk_syscalls,
        "critical_risk_syscalls": critical_risk_syscalls,
        "matched_policy_rules": matched_policy_rules,
        "risk_summary": risk_summary,
        "strace_summary": {
            "parsed_file_count": strace_result.get("parsed_file_count", 0),
            "summary_counts": strace_result.get("summary_counts", {}),
            "risk_summary": strace_result.get("risk_summary", {}),
            "syscall_policy_summary": syscall_policy_summary,
        },
        "filesystem_diff_summary": filesystem_diff.get("summary", {}),
        "runtime_violation_summary": violation_report.get("risk_summary", {}),
        "artifacts": {
            "strace_parse_result": str(Path(output_dir) / "strace_parse_result.json"),
            "filesystem_diff": str(Path(output_dir) / "filesystem_diff.json"),
            "violation_report": str(Path(output_dir) / "violation_report.json"),
            "violation_events": str(Path(output_dir) / "violation_event.jsonl"),
            "stdout": str(Path(output_dir) / "docker_run_stdout.txt"),
            "stderr": str(Path(output_dir) / "docker_run_stderr.txt"),
        },
        "final_verdict": final_verdict,
    }


def write_report(report: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "runtime_enforcement_report.json"
    md_path = out / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = report.get("strace_summary", {}).get("summary_counts", {})
    risks = report.get("risk_summary", {})
    lines = [
        "# Codex Runtime Enforcement Report",
        "",
        f"- target_platform: `{report.get('target_platform')}`",
        f"- mode: `{report.get('mode')}`",
        f"- skill_path: `{report.get('skill_path')}`",
        f"- docker_network_mode: `{report.get('docker_network_mode')}`",
        f"- sample_mount: `{report.get('sample_mount')}`",
        f"- output_mount: `{report.get('output_mount')}`",
        f"- codex_bundle_mount: `{report.get('codex_bundle_mount')}`",
        f"- real_tokens_present: `{report.get('real_tokens_present')}`",
        f"- malicious_samples_executed: `{report.get('malicious_samples_executed')}`",
        f"- container_started: `{report.get('container_started')}`",
        f"- container_killed_by_monitor: `{report.get('container_killed_by_monitor')}`",
        f"- timeout_observed: `{report.get('timeout_observed')}`",
        f"- expected_network_block: `{report.get('expected_network_block')}`",
        f"- container_removed: `{report.get('container_removed')}`",
        "",
        "## Strace Summary",
        "",
        f"- parsed_file_count: `{report.get('strace_summary', {}).get('parsed_file_count')}`",
        f"- execve: `{counts.get('execve', 0)}`",
        f"- openat: `{counts.get('openat', 0)}`",
        f"- socket: `{counts.get('socket', 0)}`",
        f"- connect: `{counts.get('connect', 0)}`",
        "",
        "## Syscall Policy Summary",
        "",
        f"- matched_policy_rules: `{len(report.get('matched_policy_rules', {}))}`",
        f"- high_risk_syscalls: `{len(report.get('high_risk_syscalls', []))}`",
        f"- critical_risk_syscalls: `{len(report.get('critical_risk_syscalls', []))}`",
        "",
        "## Risk Summary",
        "",
        f"- LOW: `{risks.get('LOW', 0)}`",
        f"- MEDIUM: `{risks.get('MEDIUM', 0)}`",
        f"- HIGH: `{risks.get('HIGH', 0)}`",
        f"- CRITICAL: `{risks.get('CRITICAL', 0)}`",
        "",
        "## Final Verdict",
        "",
        report.get("final_verdict", ""),
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}
