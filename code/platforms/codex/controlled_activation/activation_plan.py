from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_ROOT = REPO_ROOT / "analysis_results" / "controlled_skill_activation"
PLANS_DIR = OUTPUT_ROOT / "plans"


def build_activation_plan(
    sample_name: str,
    deterministic_risk: dict[str, int],
    agent_aggregate_risk: dict[str, int],
    stage21_passed: bool,
    stage23_passed: bool,
    discovery: dict[str, Any],
    policy_decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "sample_name": sample_name,
        "deterministic_risk": deterministic_risk,
        "agent_aggregate_risk": agent_aggregate_risk,
        "stage21_passed": stage21_passed,
        "stage23_passed": stage23_passed,
        "candidate_entrypoints": discovery.get("candidate_entrypoints", []),
        "allowed_entrypoints": policy_decision.get("allowed_entrypoints", []),
        "denied_entrypoints": policy_decision.get("denied_entrypoints", []),
        "requires_human_confirmation": policy_decision.get("requires_human_confirmation", False),
        "safety_boundary": {
            "network_mode": "none",
            "sample_mount": "read-only",
            "output_mount": "writable",
            "fake_home": True,
            "fake_codex_home": True,
            "sanitized_subprocess_env": True,
            "docker_sock_mounted": False,
            "privileged": False,
            "network_host": False,
            "real_tokens_passed": False,
            "codex_executed": False,
            "claude_code_executed": False,
            "strace_executed": False,
            "uploaded_scripts_executed": False,
        },
        "final_activation_decision": policy_decision.get("decision"),
        "policy_reason": policy_decision.get("reason"),
        "blockers": policy_decision.get("blockers", []),
    }


def write_activation_plan(plan: dict[str, Any], plans_dir: str | Path = PLANS_DIR) -> dict[str, str]:
    root = Path(plans_dir)
    root.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(plan["sample_name"])
    json_path = root / f"{stem}_activation_plan.json"
    md_path = root / f"{stem}_activation_plan.md"
    json_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_activation_plan(plan), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def render_activation_plan(plan: dict[str, Any]) -> str:
    lines = [
        "# Controlled Skill Activation Plan",
        "",
        f"- sample_name: `{plan.get('sample_name')}`",
        f"- final_activation_decision: `{plan.get('final_activation_decision')}`",
        f"- requires_human_confirmation: `{str(plan.get('requires_human_confirmation')).lower()}`",
        f"- stage21_passed: `{str(plan.get('stage21_passed')).lower()}`",
        f"- stage23_passed: `{str(plan.get('stage23_passed')).lower()}`",
        "",
        "## Allowed Entrypoints",
        "",
    ]
    allowed = plan.get("allowed_entrypoints") or []
    if not allowed:
        lines.append("- none")
    for item in allowed:
        lines.append(f"- `{item.get('command')}`: {item.get('reason')}")
    lines.extend(["", "## Denied Entrypoints", ""])
    denied = plan.get("denied_entrypoints") or []
    if not denied:
        lines.append("- none")
    for item in denied:
        lines.append(f"- `{item.get('command')}`: {item.get('reason')}")
    if plan.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in plan["blockers"])
    lines.append("")
    return "\n".join(lines)


def _safe_stem(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name)
