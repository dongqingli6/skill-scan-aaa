from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUTPUT_ROOT = Path("analysis_results/scaled_validation")


def write_dashboard_data(summary: dict[str, Any], output_root: Path | None = None) -> dict[str, Any]:
    root = output_root or OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    metrics = summary["metrics"]
    data = {
        "cards": [
            {"label": "Total Samples", "value": metrics["total_samples"]},
            {"label": "Real Skills", "value": metrics["real_skill_count"]},
            {"label": "Synthetic Skills", "value": metrics["synthetic_count"]},
            {"label": "Blocked", "value": metrics["blocked_count"]},
            {"label": "Manual Review", "value": metrics["manual_review_count"]},
            {"label": "F1", "value": metrics["f1"]},
        ],
        "risk_distribution": {
            "critical": metrics["critical_count"],
            "high": metrics["high_count"],
            "medium": metrics["medium_count"],
            "low": metrics["low_count"],
            "consistent": metrics["consistent_count"],
        },
        "sample_table": summary["results"],
        "stage_status": {
            "stage": summary["stage"],
            "final_status": summary["final_status"],
            "static_only": True,
            "docker_executed": False,
            "codex_executed": False,
            "claude_code_executed": False,
            "strace_executed": False,
            "network_enabled": False,
        },
        "metrics": metrics,
        "manual_review_queue": [item for item in summary["results"] if item["gate"] in ("blocked", "manual_review")],
        "artifact_paths": {
            "summary": "analysis_results/scaled_validation/summary.json",
            "report": "analysis_results/scaled_validation/report.md",
            "risk_table": "analysis_results/scaled_validation/risk_table.csv",
            "metrics": "analysis_results/scaled_validation/metrics.json",
            "confusion_matrix": "analysis_results/scaled_validation/confusion_matrix.json",
            "manual_review_queue": "analysis_results/scaled_validation/manual_review_queue.md",
            "final_research_report": "analysis_results/scaled_validation/final_research_report.md",
            "dashboard_data": "analysis_results/scaled_validation/dashboard_data.json",
        },
    }
    (root / "dashboard_data.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data
