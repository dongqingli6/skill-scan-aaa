"""Markdown report writer for static-only agent skill scans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

try:
    from core.schema_validation import iter_jsonl
except ImportError:  # pragma: no cover
    from schema_validation import iter_jsonl


def _load_json(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _line(text: Any) -> str:
    return str(text).replace("\n", " ").strip()


def _append_codex_dynamic_evidence(lines: List[str], dynamic_evidence_path: str | Path | None) -> None:
    if not dynamic_evidence_path:
        return
    path = Path(dynamic_evidence_path)
    lines.extend(["", "## Codex Dynamic Security Evidence", ""])
    if not path.exists():
        lines.extend(
            [
                f"- warning: `dynamic evidence file not found: {path}`",
                "",
                "Dynamic execution was limited to safe_skill only. No malicious samples were executed.",
                "",
            ]
        )
        return

    evidence = _load_json(path)
    fs_summary = evidence.get("filesystem_diff_summary", {})
    strace_summary = evidence.get("strace_summary", {})
    strace_counts = strace_summary.get("summary_counts", {})
    strace_risks = strace_summary.get("risk_summary", {})
    network_summary = evidence.get("network_disabled_summary", {})

    lines.extend(
        [
            "Dynamic execution was limited to safe_skill only. No malicious samples were executed.",
            "",
            f"- dynamic_execution_performed: `{evidence.get('dynamic_execution_performed')}`",
            f"- malicious_samples_executed: `{evidence.get('malicious_samples_executed')}`",
            f"- docker_network_mode: `{evidence.get('docker_network_mode')}`",
            f"- real_tokens_present: `{evidence.get('real_tokens_present')}`",
            f"- sample_mount: `{evidence.get('sample_mount')}`",
            f"- output_mount: `{evidence.get('output_mount')}`",
            f"- codex_bundle_mount: `{evidence.get('codex_bundle_mount')}`",
            "",
            "### filesystem_diff_summary",
            "",
            f"- total_created: `{fs_summary.get('total_created')}`",
            f"- total_deleted: `{fs_summary.get('total_deleted')}`",
            f"- total_modified: `{fs_summary.get('total_modified')}`",
            f"- high_risk_changes: `{fs_summary.get('high_risk_changes')}`",
            f"- critical_risk_changes: `{fs_summary.get('critical_risk_changes')}`",
            f"- risk_count: `{fs_summary.get('risk_count')}`",
            "",
            "### strace_summary",
            "",
            f"- parsed_file_count: `{strace_summary.get('parsed_file_count')}`",
            f"- execve: `{strace_counts.get('execve', 0)}`",
            f"- openat: `{strace_counts.get('openat', 0)}`",
            f"- socket: `{strace_counts.get('socket', 0)}`",
            f"- connect: `{strace_counts.get('connect', 0)}`",
            f"- risk_summary: `LOW={strace_risks.get('LOW', 0)} MEDIUM={strace_risks.get('MEDIUM', 0)} HIGH={strace_risks.get('HIGH', 0)} CRITICAL={strace_risks.get('CRITICAL', 0)}`",
            "",
            "### network_disabled_summary",
            "",
            f"- network_mode_expected: `{network_summary.get('network_mode_expected')}`",
            f"- verification_status: `{network_summary.get('verification_status')}`",
            f"- external_api_attempt_observed: `{network_summary.get('external_api_attempt_observed')}`",
            f"- external_api_blocked: `{network_summary.get('external_api_blocked')}`",
            f"- timeout_observed: `{network_summary.get('timeout_observed')}`",
            "",
            "### final_verdict",
            "",
            _line(evidence.get("final_verdict", "")),
            "",
        ]
    )


def write_markdown_report(
    *,
    static_scan_path: str | Path,
    audit_jsonl_path: str | Path,
    summary_path: str | Path,
    output_path: str | Path,
    sandbox_queue_path: str | Path | None = None,
    smoke_result_path: str | Path | None = None,
    smoke_plan_path: str | Path | None = None,
    docker_smoke_plan_path: str | Path | None = None,
    docker_preflight_path: str | Path | None = None,
    dynamic_evidence_path: str | Path | None = None,
) -> Path:
    """Generate a static-only Markdown report."""
    static_scan = _load_json(static_scan_path)
    summary = _load_json(summary_path)
    audits = iter_jsonl(audit_jsonl_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = [
        "# Agent Skill Static Security Report",
        "",
        f"- Platform: `{summary.get('platform', static_scan.get('platform', 'unknown'))}`",
        f"- Scan root: `{static_scan.get('root', '')}`",
        f"- Dynamic execution allowed: `false`",
        f"- Skill total: `{summary.get('total_skills', 0)}`",
        f"- Finding total: `{summary.get('total_findings', 0)}`",
        "",
        "## Severity Distribution",
        "",
    ]

    for severity, count in (summary.get("by_severity") or {}).items():
        lines.append(f"- {severity}: `{count}`")

    lines.extend(["", "## Classification Distribution", ""])
    for classification, count in (summary.get("by_classification") or {}).items():
        lines.append(f"- {classification}: `{count}`")

    lines.extend(["", "## Skill Risk Summary", ""])
    for audit in audits:
        lines.extend(
            [
                f"### {audit.get('skill_name', 'unknown')}",
                "",
                f"- Source path: `{audit.get('source_path', '')}`",
                f"- Classification: `{audit.get('classification', 'unknown')}`",
                f"- Severity: `{audit.get('severity', 'UNKNOWN')}`",
                f"- Confidence: `{audit.get('confidence', 0.0)}`",
                "",
            ]
        )

        findings = audit.get("static_findings") or []
        if not findings:
            lines.append("No static findings.")
            lines.append("")
            continue

        for finding in findings:
            lines.extend(
                [
                    f"- Rule: `{finding.get('rule_id', '')}`",
                    f"  Severity: `{finding.get('severity', '')}`",
                    f"  File: `{finding.get('file', '')}`",
                    f"  Evidence: `{_line(finding.get('evidence', ''))}`",
                    f"  Explanation: {_line(finding.get('explanation', ''))}",
                    f"  Recommendation: {_line(finding.get('recommendation', ''))}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Safety Recommendations",
            "",
            "- Treat SKILL.md, AGENTS.md, agents/openai.yaml, and scripts as untrusted input.",
            "- Keep dynamic execution disabled until a Docker fake HOME sandbox exists.",
            "- Do not pass real API keys, SSH keys, tokens, or real user HOME into tests.",
            "- Review repo-scoped `.agents/skills` before enabling Codex in a workspace.",
            "",
        ]
    )

    if sandbox_queue_path and Path(sandbox_queue_path).exists():
        lines.extend(["", "## Sandbox Plan", ""])
        for row in iter_jsonl(sandbox_queue_path):
            plan_path = row.get("run_plan_path")
            plan = {}
            if plan_path and Path(plan_path).exists():
                plan = _load_json(plan_path)
            lines.extend(
                [
                    f"### {row.get('skill_name', 'unknown')}",
                    "",
                    "- Dynamic execution requested: `true`",
                    "- Dynamic execution performed: `false`",
                    "- Sandbox plan generated: `true`",
                    f"- Fake HOME path: `{plan.get('fake_home', '')}`",
                    f"- Fake CODEX_HOME path: `{plan.get('fake_codex_home', '')}`",
                    f"- Network enabled: `{plan.get('network_enabled', False)}`",
                    f"- Real HOME allowed: `{row.get('real_home_allowed', False)}`",
                    f"- Real tokens allowed: `{row.get('real_tokens_allowed', False)}`",
                    "",
                ]
            )

    if smoke_result_path and Path(smoke_result_path).exists():
        result = _load_json(smoke_result_path)
        plan = _load_json(smoke_plan_path) if smoke_plan_path and Path(smoke_plan_path).exists() else {}
        lines.extend(
            [
                "",
                "## Codex Safe Smoke Test",
                "",
                "- requested: `true`",
                f"- performed: `{result.get('performed', False)}`",
                f"- success: `{result.get('success', False)}`",
                f"- safe_skill_only: `{plan.get('safe_skill_only', True)}`",
                f"- network_enabled: `{plan.get('network_enabled', False)}`",
                f"- fake_home: `{plan.get('fake_home', '')}`",
                f"- fake_codex_home: `{plan.get('fake_codex_home', '')}`",
                f"- stdout_path: `{result.get('stdout_path', '')}`",
                f"- stderr_path: `{result.get('stderr_path', '')}`",
                f"- safety_errors: `{result.get('safety_errors', [])}`",
                f"- safety_warnings: `{result.get('safety_warnings', [])}`",
                "",
                "当前报告中的 safe smoke test 不代表恶意样本动态验证。",
                "",
            ]
        )

    if docker_smoke_plan_path and docker_preflight_path and Path(docker_smoke_plan_path).exists() and Path(docker_preflight_path).exists():
        plan = _load_json(docker_smoke_plan_path)
        preflight = _load_json(docker_preflight_path)
        lines.extend(
            [
                "",
                "## Codex Docker Safe Smoke Plan",
                "",
                f"- plan_only: `{plan.get('plan_only')}`",
                f"- docker_build_allowed: `{plan.get('docker_build_allowed')}`",
                f"- docker_run_allowed: `{plan.get('docker_run_allowed')}`",
                f"- codex_exec_allowed: `{plan.get('codex_exec_allowed')}`",
                f"- network_mode: `{plan.get('network_mode')}`",
                f"- sample_mount_mode: `{plan.get('sample_mount_mode')}`",
                f"- output_mount_mode: `{plan.get('output_mount_mode')}`",
                f"- codex_bundle_mount_mode: `{plan.get('codex_bundle_mount_mode')}`",
                f"- codex_bundle_mount: `{plan.get('codex_bundle_mount')}`",
                f"- container_path: `{plan.get('container_path')}`",
                f"- fake_home_inside_container: `{plan.get('fake_home_inside_container')}`",
                f"- fake_codex_home_inside_container: `{plan.get('fake_codex_home_inside_container')}`",
                f"- command_preview: `{plan.get('command_preview')}`",
                f"- preflight_ok: `{preflight.get('ok')}`",
                f"- errors: `{preflight.get('errors')}`",
                f"- warnings: `{preflight.get('warnings')}`",
                "",
                "当前 Docker smoke plan 没有 build 镜像、没有启动容器、没有执行 Codex。",
                "",
            ]
        )

    _append_codex_dynamic_evidence(lines, dynamic_evidence_path)


    fs_diff_path = output.parent / "filesystem_diff.json"
    if fs_diff_path.exists():
        fs_diff = _load_json(fs_diff_path)
        summary = fs_diff.get("summary", {})
        lines.extend([
            "",
            "## Filesystem Diff Evidence",
            "",
            f"- total_created: `{summary.get('total_created')}`",
            f"- total_deleted: `{summary.get('total_deleted')}`",
            f"- total_modified: `{summary.get('total_modified')}`",
            f"- suspicious_changes: `{summary.get('suspicious_changes')}`",
            f"- created_files: `{fs_diff.get('created_files')}`",
            f"- deleted_files: `{fs_diff.get('deleted_files')}`",
            f"- modified_files: `{fs_diff.get('modified_files')}`",
            f"- high_risk_changes: `{fs_diff.get('high_risk_changes')}`",
            f"- critical_risk_changes: `{fs_diff.get('critical_risk_changes')}`",
            "",
            "当前 filesystem diff 仅用于 safe_skill smoke test，不代表恶意样本动态验证。",
            "",
        ])


    strace_dir = output.parent
    plan_path = strace_dir / "strace_harness_plan.json"
    policy_path = strace_dir / "strace_policy.json"
    parse_path = strace_dir / "strace_parse_result.json"
    if plan_path.exists() and policy_path.exists() and parse_path.exists():
        plan = _load_json(plan_path)
        policy = _load_json(policy_path)
        parse = _load_json(parse_path)
        lines.extend([
            "",
            "## Strace Harness Plan",
            "",
            f"- plan_only: `{plan.get('plan_only')}`",
            f"- strace_available_on_host: `{plan.get('strace_available_on_host')}`",
            f"- strace_execution_allowed: `{plan.get('strace_execution_allowed')}`",
            f"- docker_run_allowed: `{plan.get('docker_run_allowed')}`",
            f"- codex_exec_allowed: `{plan.get('codex_exec_allowed')}`",
            f"- syscall_focus: `{plan.get('syscall_focus')}`",
            f"- policy_summary: `writes={policy.get('allowed_write_prefixes')} forbidden={policy.get('forbidden_write_prefixes')}`",
            f"- parse_result_summary: `{parse.get('summary')}`",
            "",
            "当前 strace 阶段是 plan-only，没有运行 strace，也没有运行恶意样本。",
            "",
        ])

    output.write_text("\n".join(lines), encoding="utf-8")
    return output
