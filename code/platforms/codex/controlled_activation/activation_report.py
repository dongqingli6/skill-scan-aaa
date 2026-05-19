from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_ROOT = REPO_ROOT / "analysis_results" / "controlled_skill_activation"


def write_activation_outputs(summary: dict[str, Any], output_root: str | Path = OUTPUT_ROOT) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "report.md").write_text(render_report(summary), encoding="utf-8")
    (root / "activation_events.json").write_text(json.dumps(summary.get("activation_events", []), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "runtime_audit.json").write_text(json.dumps(summary.get("runtime_audit", {}), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (root / "risk_table.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["sample_name", "final_activation_decision", "requires_human_confirmation", "allowed_entrypoints", "denied_entrypoints"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in summary.get("plans", []):
            writer.writerow(
                {
                    "sample_name": item.get("sample_name"),
                    "final_activation_decision": item.get("final_activation_decision"),
                    "requires_human_confirmation": item.get("requires_human_confirmation"),
                    "allowed_entrypoints": len(item.get("allowed_entrypoints") or []),
                    "denied_entrypoints": len(item.get("denied_entrypoints") or []),
                }
            )


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Big Stage 25 Controlled Skill Activation Layer",
        "",
        f"- mode: `{summary.get('mode')}`",
        f"- plan_only: `{str(summary.get('plan_only')).lower()}`",
        f"- docker_executed: `{str(summary.get('docker_executed')).lower()}`",
        f"- codex_executed: `{str(summary.get('codex_executed')).lower()}`",
        f"- claude_code_executed: `{str(summary.get('claude_code_executed')).lower()}`",
        f"- strace_executed: `{str(summary.get('strace_executed')).lower()}`",
        f"- real_skill_executed: `{str(summary.get('real_skill_executed')).lower()}`",
        f"- network_enabled: `{str(summary.get('network_enabled')).lower()}`",
        f"- final_status: `{summary.get('final_status')}`",
        "",
        "## Plans",
        "",
    ]
    for plan in summary.get("plans", []):
        lines.append(
            f"- `{plan.get('sample_name')}`: decision `{plan.get('final_activation_decision')}`, "
            f"allowed_entrypoints `{len(plan.get('allowed_entrypoints') or [])}`"
        )
    lines.append("")
    return "\n".join(lines)
