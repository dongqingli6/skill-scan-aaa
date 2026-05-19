from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


OUTPUT_ROOT = Path("analysis_results/doc_behavior_divergence")


def write_reports(summary: dict[str, Any], output_root: Path | None = None) -> None:
    root = output_root or OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(_summary_json(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "divergence_matrix.json").write_text(json.dumps(_matrix(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_risk_table(root / "risk_table.csv", summary)
    (root / "report.md").write_text(_report_md(summary), encoding="utf-8")
    (root / "manual_review_queue.md").write_text(_manual_review_queue(summary), encoding="utf-8")


def _summary_json(summary: dict[str, Any]) -> dict[str, Any]:
    slim_results = []
    for result in summary["results"]:
        slim_results.append(
            {
                "archive_name": result["archive_name"],
                "divergence_highest": result["summary"]["divergence_highest"],
                "final_risk": result["summary"]["final_risk"],
                "decision": result["summary"]["decision"],
                "review_queue": result["summary"]["review_queue"],
                "finding_categories": [finding["category"] for finding in result["divergence_findings"]],
                "final_recommendation": result["final_recommendation"],
            }
        )
    return {key: value for key, value in summary.items() if key != "results"} | {"results": slim_results}


def _matrix(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        result["archive_name"]: {
            "claims": {
                "network": result["claims"]["claimed_network_use"]["status"],
                "filesystem": result["claims"]["claimed_filesystem_use"]["status"],
                "credential": result["claims"]["claimed_credential_use"]["status"],
                "install_setup": result["claims"]["claimed_install_setup_use"]["status"],
                "execution": result["claims"]["claimed_execution_behavior"]["status"],
                "docker": result["claims"]["claimed_docker_use"]["status"],
            },
            "evidence_flags": result["evidence"].get("evidence_flags", {}),
            "divergences": result["divergence_findings"],
            "decision": result["summary"]["decision"],
            "final_recommendation": result["final_recommendation"],
        }
        for result in summary["results"]
    }


def _write_risk_table(path: Path, summary: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["archive_name", "divergence_highest", "final_risk", "decision", "review_queue", "finding_categories"],
        )
        writer.writeheader()
        for result in summary["results"]:
            writer.writerow(
                {
                    "archive_name": result["archive_name"],
                    "divergence_highest": result["summary"]["divergence_highest"],
                    "final_risk": result["summary"]["final_risk"],
                    "decision": result["summary"]["decision"],
                    "review_queue": result["summary"]["review_queue"],
                    "finding_categories": ";".join(finding["category"] for finding in result["divergence_findings"]),
                }
            )


def _report_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Big Stage 26 Document-Behavior Divergence Analysis Layer",
        "",
        "- Mode: static existing evidence only",
        "- Skill execution: false",
        "- Docker executed: false",
        "- Codex / Claude Code executed: false",
        "- Strace executed: false",
        "- Real API called: false",
        "- Network enabled: false",
        "",
        "## Summary",
        "",
        f"- Total samples: {summary['total_samples']}",
        f"- Divergence counts: `{json.dumps(summary['divergence_counts'], sort_keys=True)}`",
        f"- Decision counts: `{json.dumps(summary['decision_counts'], sort_keys=True)}`",
        "",
        "## Per-Skill Comparison",
        "",
    ]
    for result in summary["results"]:
        claims = result["claims"]
        evidence = result["evidence"]
        lines.extend(
            [
                f"### {result['archive_name']}",
                "",
                "Claims:",
                f"- purpose: {claims.get('purpose') or 'not declared'}",
                f"- network: {claims['claimed_network_use']['status']}",
                f"- filesystem: {claims['claimed_filesystem_use']['status']}",
                f"- credentials: {claims['claimed_credential_use']['status']}",
                f"- install/setup: {claims['claimed_install_setup_use']['status']}",
                f"- execution: {claims['claimed_execution_behavior']['status']}",
                f"- docker: {claims['claimed_docker_use']['status']}",
                "",
                "Evidence:",
                f"- evidence flags: `{json.dumps(evidence.get('evidence_flags', {}), sort_keys=True)}`",
                f"- deterministic highest: {evidence.get('deterministic_highest', 'none')}",
                f"- agent highest: {evidence.get('agent_highest', 'none')}",
                "",
                "Divergence:",
            ]
        )
        if result["divergence_findings"]:
            for finding in result["divergence_findings"]:
                lines.append(f"- {finding['severity'].upper()} `{finding['category']}`: {finding['reason']}")
        else:
            lines.append("- none")
        lines.extend(["", f"Final recommendation: {result['final_recommendation']}", ""])
    return "\n".join(lines)


def _manual_review_queue(summary: dict[str, Any]) -> str:
    lines = ["# Stage 26 Manual Review Queue", ""]
    queued = [
        result
        for result in summary["results"]
        if result["summary"]["divergence_highest"] in ("critical", "high", "medium")
    ]
    if not queued:
        lines.append("No HIGH / CRITICAL / MEDIUM divergence samples.")
        return "\n".join(lines) + "\n"
    for result in queued:
        lines.append(f"## {result['archive_name']}")
        lines.append(f"- queue: {result['summary']['review_queue']}")
        lines.append(f"- highest divergence: {result['summary']['divergence_highest']}")
        lines.append(f"- final risk: {result['summary']['final_risk']}")
        lines.append(f"- recommendation: {result['final_recommendation']}")
        for finding in result["divergence_findings"]:
            lines.append(f"- {finding['severity'].upper()} {finding['category']}: {finding['reason']}")
        lines.append("")
    return "\n".join(lines)
