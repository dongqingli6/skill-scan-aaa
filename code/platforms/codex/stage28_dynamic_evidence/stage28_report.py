from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


OUTPUT_ROOT = Path("analysis_results/controlled_sinkhole_dynamic")


def write_stage28_reports(summary: dict[str, Any], output_root: Path | None = None) -> None:
    root = output_root or OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(_summary_json(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "dynamic_evidence.json").write_text(json.dumps(summary["samples"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "sinkhole_requests.json").write_text(json.dumps(summary["sinkhole_requests"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "honeypot_events.json").write_text(json.dumps(summary["honeypot_events"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "multi_session_report.json").write_text(json.dumps(summary["multi_session_events"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "platform_surface_events.json").write_text(json.dumps(summary["platform_surface_events"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_risk_table(root / "risk_table.csv", summary["samples"])
    report = _report_md(summary)
    (root / "report.md").write_text(report, encoding="utf-8")
    (root / "final_dynamic_report.md").write_text(report, encoding="utf-8")


def _summary_json(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key not in {"samples", "sinkhole_requests", "honeypot_events", "multi_session_events", "platform_surface_events"}} | {
        "samples": [
            {
                "sample": item["sample"],
                "final_verdict": item["final_verdict"],
                "honeypot_touched": item["honeypot_touched"],
                "honeypot_exfiltrated": item["honeypot_exfiltrated"],
                "platform_config_touched": item["platform_config_touched"],
                "multi_session_triggered": item["multi_session_triggered"],
            }
            for item in summary["samples"]
        ]
    }


def _write_risk_table(path: Path, samples: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample", "final_verdict", "honeypot_touched", "honeypot_exfiltrated", "sinkhole_requests", "platform_config_touched", "shadow_features"],
        )
        writer.writeheader()
        for item in samples:
            writer.writerow(
                {
                    "sample": item["sample"],
                    "final_verdict": item["final_verdict"],
                    "honeypot_touched": item["honeypot_touched"],
                    "honeypot_exfiltrated": item["honeypot_exfiltrated"],
                    "sinkhole_requests": len(item["exfil_destinations"]),
                    "platform_config_touched": item["platform_config_touched"],
                    "shadow_features": ";".join(item["shadow_features"]),
                }
            )


def _report_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Big Stage 28 Controlled Sinkhole Dynamic Evidence",
        "",
        "- real_internet_enabled: false",
        "- docker_executed: false",
        "- codex_executed: false",
        "- claude_code_executed: false",
        "- strace_executed: false",
        "- real_api_called: false",
        "- real_skill_scripts_executed: false",
        "",
        "## Samples",
        "",
    ]
    for sample in summary["samples"]:
        lines.append(f"### {sample['sample']}")
        lines.append(f"- final_verdict: `{sample['final_verdict']}`")
        lines.append(f"- honeypot_touched: `{sample['honeypot_touched']}`")
        lines.append(f"- honeypot_exfiltrated: `{sample['honeypot_exfiltrated']}`")
        lines.append(f"- multi_session_triggered: `{sample['multi_session_triggered']}`")
        lines.append(f"- platform_config_touched: `{sample['platform_config_touched']}`")
        lines.append(f"- shadow_features: `{json.dumps(sample['shadow_features'])}`")
        lines.append("")
    return "\n".join(lines)
