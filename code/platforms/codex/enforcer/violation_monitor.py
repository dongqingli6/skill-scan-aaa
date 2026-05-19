"""Violation monitor over existing Codex dynamic evidence artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path("analysis_results/codex_runtime_enforcement/violation_report.json")
FAKE_PREFIXES = ("/home/codexsafe/.codex", "/home/codexsafe/.agents", "home/codexsafe/.codex", "home/codexsafe/.agents")
SENSITIVE_MARKERS = ("/.ssh", ".env", "/home/empty/.codex", "/home/empty/.agents", "/root/.codex", "/root/.agents", "token", "credential")


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"exists": False, "path": str(p)}
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(p))
        return data
    return {"exists": True, "path": str(p), "value": data}


def is_fake_path(text: str) -> bool:
    return any(prefix in text for prefix in FAKE_PREFIXES)


def add_violation(items: list[dict[str, Any]], severity: str, category: str, evidence: Any, action: str) -> None:
    items.append({"severity": severity, "category": category, "evidence": evidence, "recommended_action": action})


def monitor_existing_evidence(
    *,
    dynamic_evidence_path: str | Path,
    strace_path: str | Path,
    filesystem_diff_path: str | Path,
    network_path: str | Path,
) -> dict[str, Any]:
    dynamic = read_json(dynamic_evidence_path)
    strace = read_json(strace_path)
    fs_diff = read_json(filesystem_diff_path)
    network = read_json(network_path)
    violations: list[dict[str, Any]] = []

    network_mode = dynamic.get("docker_network_mode") or network.get("network_mode_expected")
    for finding in strace.get("findings", []):
        category = finding.get("category")
        line = str(finding.get("line", ""))
        if category == "blocked_network_attempt" and network_mode == "none":
            add_violation(violations, "LOW", "blocked_network_attempt", finding, "record")
        elif category == "network_connect":
            add_violation(violations, "HIGH", "network_connect", finding, "kill_container")
        elif category == "sensitive_read" and not is_fake_path(line):
            add_violation(violations, finding.get("severity", "HIGH"), "sensitive_read", finding, "kill_container")
        elif category in {"safe_skill_write", "codex_bundle_write"}:
            action = "kill_container"
            add_violation(violations, finding.get("severity", "HIGH"), category, finding, action)

    evidence_text = json.dumps(strace.get("evidence", {}), ensure_ascii=False)
    if not is_fake_path(evidence_text):
        for marker in SENSITIVE_MARKERS:
            if marker.lower() in evidence_text.lower():
                add_violation(violations, "HIGH", "sensitive_path_observed", marker, "kill_container")

    for risk in fs_diff.get("risks", []):
        path = str(risk.get("path", ""))
        severity = str(risk.get("severity", "LOW")).upper()
        if path.startswith("output/"):
            add_violation(violations, "LOW", "output_write", risk, "record")
        elif "workspace/safe_skill" in path:
            add_violation(violations, "HIGH", "safe_skill_write", risk, "kill_container")
        elif "opt/codex-bundle" in path:
            add_violation(violations, "CRITICAL", "codex_bundle_write", risk, "kill_container")
        elif severity in {"HIGH", "CRITICAL"}:
            add_violation(violations, severity, "filesystem_risk", risk, "kill_container")

    risk_summary = {"INFO": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for item in violations:
        sev = item["severity"]
        risk_summary[sev] = risk_summary.get(sev, 0) + 1

    return {
        "target_platform": "codex",
        "monitor_mode": "existing_evidence",
        "network_mode": network_mode,
        "dynamic_evidence_path": str(dynamic_evidence_path),
        "strace_path": str(strace_path),
        "filesystem_diff_path": str(filesystem_diff_path),
        "network_path": str(network_path),
        "blocked_network_attempts_are_blocked": network_mode == "none",
        "real_network_connect_success_observed": any(v["category"] == "network_connect" for v in violations),
        "real_sensitive_read_observed": any(v["category"] in {"sensitive_read", "sensitive_path_observed"} for v in violations),
        "readonly_mount_write_observed": any(v["category"] in {"safe_skill_write", "codex_bundle_write"} for v in violations),
        "violations": violations,
        "risk_summary": risk_summary,
        "recommended_action": "kill_container" if risk_summary["HIGH"] or risk_summary["CRITICAL"] else "record",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor existing Codex dynamic evidence for policy violations")
    parser.add_argument("--dynamic-evidence-path", default="analysis_results/codex_dynamic_security_report/dynamic_security_report.json")
    parser.add_argument("--strace-path", default="analysis_results/codex_strace_plan/strace_parse_result.json")
    parser.add_argument("--filesystem-diff-path", default="analysis_results/codex_docker_safe_smoke_fs_diff_manual/filesystem_diff.json")
    parser.add_argument("--network-path", default="analysis_results/codex_docker_safe_smoke_manual/network_disabled_verification.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    report = monitor_existing_evidence(
        dynamic_evidence_path=args.dynamic_evidence_path,
        strace_path=args.strace_path,
        filesystem_diff_path=args.filesystem_diff_path,
        network_path=args.network_path,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
