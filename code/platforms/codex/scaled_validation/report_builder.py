from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


OUTPUT_ROOT = Path("analysis_results/scaled_validation")


def write_scaled_validation_reports(summary: dict[str, Any], output_root: Path | None = None) -> None:
    root = output_root or OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(_summary_json(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "metrics.json").write_text(json.dumps(summary["metrics"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "confusion_matrix.json").write_text(json.dumps(summary["confusion_matrix"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_risk_table(root / "risk_table.csv", summary["results"])
    (root / "manual_review_queue.md").write_text(_manual_review_queue(summary["results"]), encoding="utf-8")
    report = _final_research_report(summary)
    (root / "final_research_report.md").write_text(report, encoding="utf-8")
    (root / "report.md").write_text(report, encoding="utf-8")


def _summary_json(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key != "results"} | {
        "results": [
            {
                "archive_name": item["archive_name"],
                "sample_type": item["sample_type"],
                "sample_family": item["sample_family"],
                "final_severity": item["final_severity"],
                "gate": item["gate"],
                "divergence": item["divergence"],
            }
            for item in summary["results"]
        ]
    }


def _write_risk_table(path: Path, results: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["archive_name", "sample_type", "sample_family", "static_severity", "divergence", "final_severity", "gate", "finding_categories"],
        )
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "archive_name": item["archive_name"],
                    "sample_type": item["sample_type"],
                    "sample_family": item["sample_family"],
                    "static_severity": item["static_severity"],
                    "divergence": item["divergence"],
                    "final_severity": item["final_severity"],
                    "gate": item["gate"],
                    "finding_categories": ";".join(item.get("finding_categories", [])),
                }
            )


def _manual_review_queue(results: list[dict[str, Any]]) -> str:
    lines = ["# Stage 27 Manual Review Queue", ""]
    queued = [item for item in results if item["gate"] in ("blocked", "manual_review")]
    if not queued:
        lines.append("No blocked or manual-review samples.")
        return "\n".join(lines) + "\n"
    for item in queued:
        lines.append(f"## {item['archive_name']}")
        lines.append(f"- sample_type: {item['sample_type']}")
        lines.append(f"- family: {item['sample_family']}")
        lines.append(f"- final_severity: {item['final_severity']}")
        lines.append(f"- gate: {item['gate']}")
        lines.append(f"- divergence: {item['divergence']}")
        lines.append(f"- recommendation: {item['recommendation']}")
        lines.append("")
    return "\n".join(lines)


def _final_research_report(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    sections = [
        ("Executive Summary", f"Stage 27 evaluates {summary['total_samples']} samples using static-only evidence aggregation: {summary['real_skill_count']} real skills and {summary['synthetic_count']} synthetic fixtures."),
        ("System Overview", "The pipeline combines deterministic static results, mock agent static aggregation, document-behavior divergence analysis, low-risk dynamic monitoring summaries, and synthetic runtime violation evidence."),
        ("Safety Boundary", "This stage does not execute skills, run container workloads, run Codex or Claude Code, run syscall tracing, call real APIs, or enable network access. Synthetic attack-like fixtures contain fake placeholders only."),
        ("Dataset", f"Real skills: {summary['real_skill_count']}. Synthetic skills: {summary['synthetic_count']} with benign, suspicious, and attack-like families."),
        ("Real Skill Results", _table(summary["results"], "real")),
        ("Synthetic Corpus Results", _table(summary["results"], "synthetic")),
        ("Agent-assisted Static Analysis Results", "Agent-assisted results are consumed from existing mock/static summaries; agent output cannot lower deterministic risk."),
        ("Document-Behavior Divergence Results", "Stage 26 evidence is included. Divergence can raise final risk but cannot lower existing risk."),
        ("Runtime Synthetic Violation Results", "Stage 24 synthetic runtime violation evidence is included as prior dynamic evidence; no new runtime execution is performed."),
        ("Low-risk Dynamic Monitoring Results", "Stage 23 low-risk monitoring evidence is included for previously approved benign inspection candidates only."),
        ("Metrics", json.dumps(metrics, indent=2, sort_keys=True)),
        ("False Positives / False Negatives", f"FP={metrics['false_positive']}; FN={metrics['false_negative']}; suspicious samples are counted separately as manual-review targets."),
        ("Manual Review Queue", "See analysis_results/scaled_validation/manual_review_queue.md."),
        ("Limitations", "This is a research prototype. Static-only synthetic validation is useful for regression coverage but is not a production-grade security guarantee."),
        ("Future Work", "Add broader curated corpora, human-reviewed labels, richer static parsers, and separately approved controlled activation smoke tests."),
        ("Conclusion", "Stage 27 produces scaled static validation artifacts and a final research report while preserving the no-execution safety boundary."),
    ]
    lines: list[str] = ["# Big Stage 27 Scaled Validation and Final Reporting Layer", ""]
    for title, body in sections:
        lines.extend([f"## {title}", "", body, ""])
    return "\n".join(lines)


def _table(results: list[dict[str, Any]], sample_type: str) -> str:
    selected = [item for item in results if item["sample_type"] == sample_type]
    if not selected:
        return "No samples."
    lines = ["| Sample | Family | Severity | Gate |", "|---|---|---|---|"]
    for item in selected:
        lines.append(f"| `{item['archive_name']}` | `{item['sample_family']}` | `{item['final_severity']}` | `{item['gate']}` |")
    return "\n".join(lines)
