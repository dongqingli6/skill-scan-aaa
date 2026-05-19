from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SEVERITIES = ("critical", "high", "medium", "low", "informational")
SEVERITY_RANK = {"informational": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def aggregate_agent_result(deterministic: dict[str, Any], agent_report: dict[str, Any]) -> dict[str, Any]:
    deterministic_risk = _risk_from_mapping(deterministic)
    agent_risk = _risk_from_mapping(agent_report.get("risk_summary", {}))
    final_risk = {severity: max(deterministic_risk[severity], agent_risk[severity]) for severity in SEVERITIES}
    deterministic_highest = _highest_severity(deterministic_risk)
    agent_highest = _highest_severity(agent_risk)
    final_highest = _highest_severity(final_risk)
    agent_failed = bool(agent_report.get("agent_failed") or agent_report.get("parse_error") or agent_report.get("timeout"))
    recommended_gate = _recommended_gate(final_risk, agent_failed=agent_failed)
    return {
        "sample_name": deterministic.get("archive_name", agent_report.get("sample_name", "unknown")),
        "deterministic_risk_summary": deterministic_risk,
        "agent_risk_summary": agent_risk,
        "final_risk_summary": final_risk,
        "deterministic_highest": deterministic_highest,
        "agent_highest": agent_highest,
        "final_highest": final_highest,
        "agent_failed": agent_failed,
        "agent_can_lower_risk": False,
        "recommended_gate": recommended_gate,
        "can_execute_dynamically": recommended_gate == "allowed_for_manual_review",
        "requires_human_review": recommended_gate != "allowed_for_manual_review",
        "blockers": _blockers(final_risk, agent_failed=agent_failed),
    }


def write_aggregated_result(result: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _risk_from_mapping(mapping: dict[str, Any]) -> dict[str, int]:
    return {severity: int(mapping.get(severity, 0) or 0) for severity in SEVERITIES}


def _highest_severity(risk: dict[str, int]) -> str:
    highest = "none"
    highest_rank = -1
    for severity in SEVERITIES:
        if risk.get(severity, 0) > 0 and SEVERITY_RANK[severity] > highest_rank:
            highest = severity
            highest_rank = SEVERITY_RANK[severity]
    return highest


def _recommended_gate(risk: dict[str, int], *, agent_failed: bool) -> str:
    if risk["critical"] > 0 or risk["high"] > 0:
        return "denied"
    if agent_failed:
        return "manual_review"
    if risk["medium"] > 0:
        return "manual_review"
    return "allowed_for_manual_review"


def _blockers(risk: dict[str, int], *, agent_failed: bool) -> list[str]:
    blockers: list[str] = []
    if risk["critical"] > 0 or risk["high"] > 0:
        blockers.append("HIGH / CRITICAL static findings block dynamic execution")
    if agent_failed:
        blockers.append("agent-assisted static analysis failed; cannot automatically allow")
    return blockers
