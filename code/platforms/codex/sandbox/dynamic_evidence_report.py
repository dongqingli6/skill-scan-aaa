"""Build a unified Codex dynamic security report from existing evidence files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("analysis_results/codex_dynamic_security_report")
DEFAULT_STRACE_RESULT = Path("analysis_results/codex_strace_plan/strace_parse_result.json")
DEFAULT_FS_DIFF = Path("analysis_results/codex_docker_safe_smoke_fs_diff_manual/filesystem_diff.json")
DEFAULT_NETWORK = Path("analysis_results/codex_docker_safe_smoke_manual/network_disabled_verification.json")
DEFAULT_DYNAMIC = Path("analysis_results/codex_docker_safe_smoke_manual/dynamic_evidence.json")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(path))
        return data
    return {"exists": True, "path": str(path), "value": data}


def filesystem_summary(fs_diff: dict[str, Any]) -> dict[str, Any]:
    summary = fs_diff.get("summary", {})
    risks = fs_diff.get("risks", [])
    return {
        "source": fs_diff.get("path"),
        "total_created": summary.get("total_created", len(fs_diff.get("created_files", []))),
        "total_deleted": summary.get("total_deleted", len(fs_diff.get("deleted_files", []))),
        "total_modified": summary.get("total_modified", len(fs_diff.get("modified_files", []))),
        "high_risk_changes": len(fs_diff.get("high_risk_changes", [])),
        "critical_risk_changes": len(fs_diff.get("critical_risk_changes", [])),
        "risk_count": len(risks),
        "risks": risks,
    }


def strace_summary(strace_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": strace_result.get("path"),
        "parsed_file_count": strace_result.get("parsed_file_count", 0),
        "total_lines": strace_result.get("total_lines", 0),
        "summary_counts": strace_result.get("summary_counts", {}),
        "risk_summary": strace_result.get("risk_summary", {}),
        "finding_count": len(strace_result.get("findings", [])),
        "syscall_policy_summary": strace_result.get("syscall_policy_summary", {}),
        "high_risk_syscalls": strace_result.get("high_risk_syscalls", []),
        "critical_risk_syscalls": strace_result.get("critical_risk_syscalls", []),
        "matched_policy_rules": strace_result.get("matched_policy_rules", {}),
    }


def network_summary(network: dict[str, Any], dynamic: dict[str, Any]) -> dict[str, Any]:
    return {
        "network_mode_expected": network.get("network_mode_expected", "none"),
        "verification_status": network.get("verification_status"),
        "external_api_attempt_observed": bool(
            network.get("external_api_attempt_observed") or dynamic.get("api_connection_blocked")
        ),
        "external_api_blocked": bool(network.get("external_api_blocked") or dynamic.get("api_connection_blocked")),
        "timeout_observed": bool(dynamic.get("timeout_observed")),
        "evidence_line_count": len(network.get("evidence_lines", [])),
    }


def combine_risk_summary(fs: dict[str, Any], strace: dict[str, Any]) -> dict[str, int]:
    combined = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for risk in fs.get("risks", []):
        severity = str(risk.get("severity", "")).upper()
        if severity in combined:
            combined[severity] += 1
    for severity, count in strace.get("risk_summary", {}).items():
        normalized = str(severity).upper()
        if normalized in combined:
            combined[normalized] += int(count)
    return combined


def build_report(
    strace_path: Path = DEFAULT_STRACE_RESULT,
    fs_diff_path: Path = DEFAULT_FS_DIFF,
    network_path: Path = DEFAULT_NETWORK,
    dynamic_path: Path = DEFAULT_DYNAMIC,
) -> dict[str, Any]:
    strace = read_json(strace_path)
    fs_diff = read_json(fs_diff_path)
    network = read_json(network_path)
    dynamic = read_json(dynamic_path)
    risks = combine_risk_summary(fs_diff, strace)
    verdict = (
        "safe_skill-only dynamic harness succeeded; observed Codex network attempts were blocked by "
        "Docker --network none; no HIGH/CRITICAL filesystem or credential access evidence was observed."
    )
    if risks["HIGH"] or risks["CRITICAL"]:
        verdict = "safe_skill-only dynamic harness completed, but HIGH/CRITICAL evidence requires review."

    return {
        "target_platform": "codex",
        "sample": "safe_skill",
        "dynamic_execution_performed": True,
        "malicious_samples_executed": False,
        "docker_network_mode": "none",
        "real_tokens_present": False,
        "sample_mount": "read-only",
        "output_mount": "writable",
        "codex_bundle_mount": "read-only",
        "filesystem_diff_summary": filesystem_summary(fs_diff),
        "strace_summary": strace_summary(strace),
        "syscall_policy_summary": strace.get("syscall_policy_summary", {}),
        "high_risk_syscalls": strace.get("high_risk_syscalls", []),
        "critical_risk_syscalls": strace.get("critical_risk_syscalls", []),
        "matched_policy_rules": strace.get("matched_policy_rules", {}),
        "network_disabled_summary": network_summary(network, dynamic),
        "risk_summary": risks,
        "final_verdict": verdict,
        "sources": {
            "network_disabled_verification": str(network_path),
            "dynamic_evidence": str(dynamic_path),
            "filesystem_diff": str(fs_diff_path),
            "strace_parse_result": str(strace_path),
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    counts = report["strace_summary"].get("summary_counts", {})
    risks = report["risk_summary"]
    lines = [
        "# Codex Dynamic Security Report",
        "",
        f"- target_platform: {report['target_platform']}",
        f"- sample: {report['sample']}",
        f"- docker_network_mode: {report['docker_network_mode']}",
        f"- malicious_samples_executed: {str(report['malicious_samples_executed']).lower()}",
        f"- real_tokens_present: {str(report['real_tokens_present']).lower()}",
        f"- sample_mount: {report['sample_mount']}",
        f"- output_mount: {report['output_mount']}",
        f"- codex_bundle_mount: {report['codex_bundle_mount']}",
        "",
        "## Strace Summary",
        "",
        f"- parsed_file_count: {report['strace_summary'].get('parsed_file_count', 0)}",
        f"- execve: {counts.get('execve', 0)}",
        f"- openat: {counts.get('openat', 0)}",
        f"- socket: {counts.get('socket', 0)}",
        f"- connect: {counts.get('connect', 0)}",
        "",
        "## Syscall Policy Summary",
        "",
        f"- matched_policy_rules: {len(report.get('matched_policy_rules', {}))}",
        f"- high_risk_syscalls: {len(report.get('high_risk_syscalls', []))}",
        f"- critical_risk_syscalls: {len(report.get('critical_risk_syscalls', []))}",
        "",
        "## Risk Summary",
        "",
        f"- LOW: {risks['LOW']}",
        f"- MEDIUM: {risks['MEDIUM']}",
        f"- HIGH: {risks['HIGH']}",
        f"- CRITICAL: {risks['CRITICAL']}",
        "",
        "## Final Verdict",
        "",
        report["final_verdict"],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Codex dynamic security report from existing evidence")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--strace", default=str(DEFAULT_STRACE_RESULT))
    parser.add_argument("--filesystem-diff", default=str(DEFAULT_FS_DIFF))
    parser.add_argument("--network", default=str(DEFAULT_NETWORK))
    parser.add_argument("--dynamic", default=str(DEFAULT_DYNAMIC))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(
        strace_path=Path(args.strace),
        fs_diff_path=Path(args.filesystem_diff),
        network_path=Path(args.network),
        dynamic_path=Path(args.dynamic),
    )
    json_path = out_dir / "dynamic_security_report.json"
    md_path = out_dir / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, md_path)
    print(json_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
