from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
OUTPUT_ROOT = REPO_ROOT / "analysis_results" / "runtime_violation_synthetic_live"


def write_runtime_violation_outputs(
    events: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    summary: dict[str, Any],
    output_root: Path | None = None,
) -> None:
    output_root = OUTPUT_ROOT if output_root is None else output_root
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / "violation_event.json").write_text(json.dumps(events, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {"findings": findings, "decisions": decisions, "summary": summary}
    (output_root / "violation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(render_markdown_report(events, findings, decisions, summary), encoding="utf-8")
    write_risk_table(output_root / "risk_table.csv", findings, decisions)


def write_risk_table(path: Path, findings: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> None:
    decision_by_event = {decision.get("event_id"): decision for decision in decisions}
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["event_id", "event_type", "severity", "category", "matched_rule", "action", "runtime_response", "synthetic", "dry_run"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for finding in findings:
            decision = decision_by_event.get(finding.get("event_id"), {})
            writer.writerow(
                {
                    "event_id": finding.get("event_id"),
                    "event_type": finding.get("event_type"),
                    "severity": finding.get("severity"),
                    "category": finding.get("category"),
                    "matched_rule": finding.get("matched_rule"),
                    "action": finding.get("action"),
                    "runtime_response": decision.get("runtime_response"),
                    "synthetic": finding.get("synthetic"),
                    "dry_run": finding.get("dry_run"),
                }
            )


def render_markdown_report(
    events: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Stage 24 Synthetic Runtime Violation Live Test",
        "",
        "This report is generated from synthetic runtime events and a fake kill callback only.",
        "",
        f"- total_events: `{summary.get('total_events')}`",
        f"- critical: `{summary.get('critical')}`",
        f"- high: `{summary.get('high')}`",
        f"- medium: `{summary.get('medium')}`",
        f"- low: `{summary.get('low')}`",
        f"- kill_decisions: `{summary.get('kill_decisions')}`",
        f"- fail_closed_decisions: `{summary.get('fail_closed_decisions')}`",
        f"- record_only_decisions: `{summary.get('record_only_decisions')}`",
        f"- fake_kill_callback_called: `{str(summary.get('fake_kill_callback_called')).lower()}`",
        f"- real_container_killed: `{str(summary.get('real_container_killed')).lower()}`",
        f"- docker_executed: `{str(summary.get('docker_executed')).lower()}`",
        f"- codex_executed: `{str(summary.get('codex_executed')).lower()}`",
        f"- strace_executed: `{str(summary.get('strace_executed')).lower()}`",
        f"- real_skill_executed: `{str(summary.get('real_skill_executed')).lower()}`",
        f"- network_enabled: `{str(summary.get('network_enabled')).lower()}`",
        f"- final_status: `{summary.get('final_status')}`",
        "",
        "## Findings",
        "",
    ]
    decision_by_event = {decision.get("event_id"): decision for decision in decisions}
    for finding in findings:
        decision = decision_by_event.get(finding.get("event_id"), {})
        lines.append(
            f"- `{finding.get('event_type')}`: severity `{finding.get('severity')}`, "
            f"action `{finding.get('action')}`, response `{decision.get('runtime_response')}`"
        )
    lines.append("")
    return "\n".join(lines)
