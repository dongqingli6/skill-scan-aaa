#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_STATIC_ROOT = REPO_ROOT / "code" / "platforms" / "codex" / "agent_static_analysis"
if str(AGENT_STATIC_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_STATIC_ROOT))

import agent_result_aggregator
import agent_static_analyzer


OUTPUT_ROOT = REPO_ROOT / "analysis_results" / "agent_static_analysis"
AGENT_REPORTS_DIR = OUTPUT_ROOT / "agent_reports"
AGGREGATED_DIR = OUTPUT_ROOT / "aggregated"


def ensure_output_dirs() -> None:
    for path in (OUTPUT_ROOT, AGENT_REPORTS_DIR, AGGREGATED_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_real_skill_dashboard(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_agent_static_analysis(dashboard_path: str | Path, *, provider: str = agent_static_analyzer.DEFAULT_PROVIDER) -> dict[str, Any]:
    ensure_output_dirs()
    dashboard = load_real_skill_dashboard(dashboard_path)
    samples = dashboard.get("samples", [])
    results = []
    for sample in samples:
        agent_report = agent_static_analyzer.analyze_sample_static(sample, provider=provider, output_dir=AGENT_REPORTS_DIR)
        aggregated = agent_result_aggregator.aggregate_agent_result(sample, agent_report)
        stem = _safe_stem(str(sample.get("archive_name", "unknown")))
        agent_result_aggregator.write_aggregated_result(aggregated, AGGREGATED_DIR / f"{stem}_aggregated_risk.json")
        results.append({"sample": sample, "agent_report": agent_report, "aggregated": aggregated})
    summary = build_summary(results, provider=provider)
    write_outputs(summary, results)
    return summary


def build_summary(results: list[dict[str, Any]], *, provider: str) -> dict[str, Any]:
    return {
        "stage": "Stage 25A Agent-assisted Static Analysis Prototype",
        "provider": provider,
        "provider_is_mock": provider == "mock",
        "total_samples": len(results),
        "agent_failed_count": sum(1 for item in results if item["agent_report"].get("agent_failed")),
        "denied_count": sum(1 for item in results if item["aggregated"].get("recommended_gate") == "denied"),
        "manual_review_count": sum(1 for item in results if item["aggregated"].get("recommended_gate") == "manual_review"),
        "allowed_for_manual_review_count": sum(1 for item in results if item["aggregated"].get("recommended_gate") == "allowed_for_manual_review"),
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "network_enabled": False,
        "real_tokens_read": False,
        "real_tokens_sent": False,
        "results": [
            {
                "archive_name": item["sample"].get("archive_name"),
                "deterministic_highest": item["aggregated"].get("deterministic_highest"),
                "agent_highest": item["aggregated"].get("agent_highest"),
                "final_highest": item["aggregated"].get("final_highest"),
                "recommended_gate": item["aggregated"].get("recommended_gate"),
                "agent_failed": item["aggregated"].get("agent_failed"),
            }
            for item in results
        ],
        "final_status": "pass",
    }


def write_outputs(summary: dict[str, Any], results: list[dict[str, Any]]) -> None:
    ensure_output_dirs()
    (OUTPUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "report.md").write_text(render_report(summary), encoding="utf-8")
    with (OUTPUT_ROOT / "risk_table.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["archive_name", "deterministic_highest", "agent_highest", "final_highest", "recommended_gate", "agent_failed"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in summary["results"]:
            writer.writerow({field: item.get(field) for field in fields})


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Stage 25A Agent-assisted Static Analysis Prototype",
        "",
        f"- provider: `{summary.get('provider')}`",
        f"- provider_is_mock: `{str(summary.get('provider_is_mock')).lower()}`",
        f"- total_samples: `{summary.get('total_samples')}`",
        f"- denied_count: `{summary.get('denied_count')}`",
        f"- manual_review_count: `{summary.get('manual_review_count')}`",
        f"- allowed_for_manual_review_count: `{summary.get('allowed_for_manual_review_count')}`",
        f"- docker_executed: `{str(summary.get('docker_executed')).lower()}`",
        f"- codex_executed: `{str(summary.get('codex_executed')).lower()}`",
        f"- claude_code_executed: `{str(summary.get('claude_code_executed')).lower()}`",
        f"- strace_executed: `{str(summary.get('strace_executed')).lower()}`",
        f"- real_skill_executed: `{str(summary.get('real_skill_executed')).lower()}`",
        f"- network_enabled: `{str(summary.get('network_enabled')).lower()}`",
        f"- final_status: `{summary.get('final_status')}`",
        "",
        "## Results",
        "",
    ]
    for item in summary["results"]:
        lines.append(
            f"- `{item.get('archive_name')}`: deterministic `{item.get('deterministic_highest')}`, "
            f"agent `{item.get('agent_highest')}`, final `{item.get('final_highest')}`, gate `{item.get('recommended_gate')}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 25A agent-assisted static analysis prototype")
    parser.add_argument("--real-skill-dashboard", required=True)
    parser.add_argument("--provider", choices=["none", "mock", "codex", "claude"], default=agent_static_analyzer.DEFAULT_PROVIDER)
    return parser.parse_args()


def _safe_stem(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name)


def main() -> int:
    args = parse_args()
    summary = run_agent_static_analysis(args.real_skill_dashboard, provider=args.provider)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
