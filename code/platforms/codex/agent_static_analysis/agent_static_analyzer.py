from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SEVERITIES = ("critical", "high", "medium", "low", "informational")
DEFAULT_PROVIDER = "mock"
PROMPT_PATH = Path(__file__).resolve().parent / "agent_static_prompt.md"


def build_redacted_prompt(sample: dict[str, Any], deterministic_findings: list[dict[str, Any]] | None = None) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    safe_sample = {
        "archive_name": sample.get("archive_name"),
        "sample_id": sample.get("sample_id"),
        "file_count": sample.get("file_count"),
        "has_skill_md": sample.get("has_skill_md"),
        "has_scripts": sample.get("has_scripts"),
        "has_env_file": sample.get("has_env_file"),
        "has_ssh_references": sample.get("has_ssh_references"),
        "has_docker_references": sample.get("has_docker_references"),
        "has_network_references": sample.get("has_network_references"),
        "risk_summary": _risk_from_sample(sample),
        "deterministic_findings": _redact_findings(deterministic_findings or sample.get("high_findings") or []),
    }
    return prompt + "\n\n## Redacted Static Context\n\n```json\n" + json.dumps(safe_sample, indent=2, sort_keys=True) + "\n```\n"


def analyze_sample_static(
    sample: dict[str, Any],
    *,
    provider: str = DEFAULT_PROVIDER,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    if provider == "none":
        report = _base_report(sample, provider)
        report.update(
            {
                "agent_failed": True,
                "notes": "provider none selected; agent-assisted analysis not run",
                "recommended_gate": "manual_review",
                "can_execute_dynamically": False,
                "requires_human_review": True,
            }
        )
    elif provider == "mock":
        report = _mock_provider_report(sample)
    elif provider in {"codex", "claude"}:
        report = _base_report(sample, provider)
        report.update(
            {
                "agent_failed": True,
                "notes": f"provider {provider} is reserved and disabled in Stage 25A",
                "recommended_gate": "manual_review",
                "can_execute_dynamically": False,
                "requires_human_review": True,
            }
        )
    else:
        raise ValueError(f"unsupported provider: {provider}")

    if output_dir is not None:
        write_agent_report(report, Path(output_dir))
    return report


def write_agent_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(str(report["sample_name"]))
    json_path = output_dir / f"{stem}_agent_static_report.json"
    md_path = output_dir / f"{stem}_agent_static_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_agent_report_md(report), encoding="utf-8")


def render_agent_report_md(report: dict[str, Any]) -> str:
    summary = report.get("risk_summary", {})
    lines = [
        "# Agent-assisted Static Analysis Report",
        "",
        f"- agent_name: `{report.get('agent_name')}`",
        f"- analysis_mode: `{report.get('analysis_mode')}`",
        f"- sample_name: `{report.get('sample_name')}`",
        f"- recommended_gate: `{report.get('recommended_gate')}`",
        f"- can_execute_dynamically: `{str(report.get('can_execute_dynamically')).lower()}`",
        f"- requires_human_review: `{str(report.get('requires_human_review')).lower()}`",
        f"- agent_failed: `{str(report.get('agent_failed')).lower()}`",
        f"- parse_error: `{str(report.get('parse_error')).lower()}`",
        f"- timeout: `{str(report.get('timeout')).lower()}`",
        f"- risk_summary: `C{summary.get('critical', 0)} H{summary.get('high', 0)} M{summary.get('medium', 0)} L{summary.get('low', 0)} I{summary.get('informational', 0)}`",
        "",
        "## Findings",
        "",
    ]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- none")
    for finding in findings:
        lines.append(f"- `{finding.get('severity')}` `{finding.get('category')}` in `{finding.get('file')}`: {finding.get('reason')}")
    lines.extend(["", "## Notes", "", str(report.get("notes", "")), ""])
    return "\n".join(lines)


def _mock_provider_report(sample: dict[str, Any]) -> dict[str, Any]:
    report = _base_report(sample, "mock")
    sample_name = str(sample.get("archive_name", "unknown"))
    deterministic = _risk_from_sample(sample)
    findings: list[dict[str, Any]] = []
    risk = {severity: 0 for severity in SEVERITIES}

    if deterministic["high"] > 0 or deterministic["critical"] > 0:
        risk["high"] = max(1, deterministic["high"])
        findings.append(_finding("high", "network_or_credential_example", sample, "Mock agent confirms deterministic HIGH context requires blocking."))
    elif deterministic["medium"] > 0 or sample.get("has_network_references"):
        risk["medium"] = max(1, deterministic["medium"])
        findings.append(_finding("medium", "manual_review_network_reference", sample, "Mock agent keeps network-related documentation under manual review."))
    else:
        risk["informational"] = 0

    gate = _gate_from_risk(risk, agent_failed=False)
    report.update(
        {
            "risk_summary": risk,
            "findings": findings,
            "recommended_gate": gate,
            "can_execute_dynamically": gate == "allowed_for_manual_review",
            "requires_human_review": gate != "allowed_for_manual_review",
            "notes": f"mock provider only; no real API call for {sample_name}",
        }
    )
    return report


def _base_report(sample: dict[str, Any], provider: str) -> dict[str, Any]:
    return {
        "agent_name": f"stage25a-{provider}",
        "analysis_mode": "agent_assisted_static_only",
        "sample_name": str(sample.get("archive_name", "unknown")),
        "files_reviewed": ["file_tree", "SKILL.md metadata", "deterministic static findings"],
        "risk_summary": {severity: 0 for severity in SEVERITIES},
        "findings": [],
        "recommended_gate": "manual_review",
        "can_execute_dynamically": False,
        "requires_human_review": True,
        "agent_failed": False,
        "parse_error": False,
        "timeout": False,
        "notes": "",
    }


def _risk_from_sample(sample: dict[str, Any]) -> dict[str, int]:
    return {severity: int(sample.get(severity, 0) or 0) for severity in SEVERITIES}


def _gate_from_risk(risk: dict[str, int], *, agent_failed: bool) -> str:
    if agent_failed:
        return "manual_review"
    if risk.get("critical", 0) > 0 or risk.get("high", 0) > 0:
        return "denied"
    if risk.get("medium", 0) > 0:
        return "manual_review"
    return "allowed_for_manual_review"


def _finding(severity: str, category: str, sample: dict[str, Any], reason: str) -> dict[str, Any]:
    high_findings = sample.get("high_findings") or []
    first = high_findings[0] if high_findings else {}
    return {
        "severity": severity,
        "category": category,
        "file": str(first.get("file", "SKILL.md")),
        "line": int(first.get("line", 0) or 0),
        "evidence": str(first.get("context", ""))[:160],
        "reason": reason,
        "confidence": "medium",
    }


def _redact_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted = []
    for finding in findings[:20]:
        redacted.append(
            {
                "severity": finding.get("severity"),
                "category": finding.get("finding_type", finding.get("category", "")),
                "file": finding.get("file"),
                "line": finding.get("line"),
                "reason": finding.get("reason"),
                "context": str(finding.get("context", ""))[:160],
            }
        )
    return redacted


def _safe_stem(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name)
