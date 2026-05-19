from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import activation_plan
import activation_policy
import activation_report
import entrypoint_discovery


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RUNTIME_IMAGE = "python:3.11-slim"
FAKE_HOME = "/home/codexsafe"
FAKE_CODEX_HOME = "/home/codexsafe/.codex"


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_controlled_activation_plan(
    *,
    inbox: Path,
    sample_names: list[str],
    plan_only: bool = True,
    require_human_approved: bool = False,
    max_commands_per_sample: int = 1,
) -> dict[str, Any]:
    stage20 = load_json(REPO_ROOT / "analysis_results" / "real_skill_batch_static_dashboard" / "summary.json")
    stage23 = load_json(REPO_ROOT / "analysis_results" / "real_skill_dynamic_monitoring_batch" / "summary.json")
    plans: list[dict[str, Any]] = []
    for sample_name in sample_names:
        sample = _sample_by_name(stage20, sample_name)
        deterministic_risk = _risk_from_sample(sample)
        agent_risk = _load_agent_aggregate_risk(sample_name)
        extracted_dir = _extracted_skill_dir(sample)
        discovery = entrypoint_discovery.discover_candidate_entrypoints(extracted_dir)
        stage23_passed = _stage23_passed(stage23, sample_name)
        policy_decision = activation_policy.evaluate_activation_policy(
            sample_name,
            deterministic_risk,
            agent_risk,
            discovery["candidate_entrypoints"],
            stage21_passed=stage23_passed,
            stage23_passed=stage23_passed,
            human_confirmed=require_human_approved and not plan_only,
        )
        plan = activation_plan.build_activation_plan(
            sample_name,
            deterministic_risk,
            agent_risk,
            stage21_passed=stage23_passed,
            stage23_passed=stage23_passed,
            discovery=discovery,
            policy_decision=policy_decision,
        )
        activation_plan.write_activation_plan(plan, activation_plan.PLANS_DIR)
        plans.append(plan)
    summary = {
        "stage": "Big Stage 25 Controlled Skill Activation Layer",
        "mode": "plan_only" if plan_only else "controlled_activation",
        "plan_only": plan_only,
        "plans": plans,
        "activation_events": [],
        "runtime_audit": {
            "docker_executed": False,
            "codex_executed": False,
            "claude_code_executed": False,
            "strace_executed": False,
            "real_skill_executed": False,
            "network_enabled": False,
            "uploaded_scripts_executed": False,
            "real_tokens_passed": False,
        },
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "network_enabled": False,
        "final_status": "plan_generated",
    }
    activation_report.write_activation_outputs(summary, activation_report.OUTPUT_ROOT)
    return summary


def build_activation_docker_command(
    sample_id: str,
    skill_path: Path,
    output_dir: Path,
    safe_command: str,
    image: str = DEFAULT_RUNTIME_IMAGE,
) -> dict[str, Any]:
    decision = activation_policy.evaluate_entrypoint_command(safe_command)
    if not decision["allowed"]:
        raise ValueError(decision["reason"])
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        f"codex-controlled-activation-{sample_id}",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev",
        "--tmpfs",
        "/run:rw,noexec,nosuid,nodev",
        "--pids-limit",
        "128",
        "--memory",
        "256m",
        "--cpus",
        "1.0",
        "-e",
        f"HOME={FAKE_HOME}",
        "-e",
        f"CODEX_HOME={FAKE_CODEX_HOME}",
        "-v",
        f"{skill_path.resolve()}:/workspace/skill:ro",
        "-v",
        f"{output_dir.resolve()}:/output:rw",
        image,
        safe_command,
    ]
    return {
        "command": command,
        "runtime_image": image,
        "network_mode": "none",
        "sample_mount_mode": "read-only",
        "output_mount_mode": "writable",
        "fake_home_used": True,
        "fake_codex_home_used": True,
        "sanitized_subprocess_env": True,
        "docker_sock_mounted": False,
        "privileged": False,
        "network_host": False,
        "docker_pull_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "uploaded_scripts_executed": False,
    }


def inspect_local_image_command(image: str = DEFAULT_RUNTIME_IMAGE) -> list[str]:
    return ["docker", "image", "inspect", image]


def sanitized_subprocess_env() -> dict[str, str]:
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": FAKE_HOME, "CODEX_HOME": FAKE_CODEX_HOME}


def _sample_by_name(stage20_summary: dict[str, Any], sample_name: str) -> dict[str, Any]:
    for sample in stage20_summary.get("samples", []):
        if sample.get("archive_name") == sample_name:
            return sample
    return {"archive_name": sample_name}


def _risk_from_sample(sample: dict[str, Any]) -> dict[str, int]:
    return {severity: int(sample.get(severity, 0) or 0) for severity in ("critical", "high", "medium", "low", "informational")}


def _load_agent_aggregate_risk(sample_name: str) -> dict[str, int]:
    path = REPO_ROOT / "analysis_results" / "agent_static_analysis" / "aggregated" / f"{_safe_stem(sample_name)}_aggregated_risk.json"
    if not path.exists():
        return {"critical": 0, "high": 1, "medium": 0, "low": 0, "informational": 0}
    data = load_json(path)
    return data.get("final_risk_summary", {})


def _extracted_skill_dir(sample: dict[str, Any]) -> Path:
    sample_id = str(sample.get("sample_id", "missing"))
    return REPO_ROOT / "analysis_results" / "real_skill_intake" / "quarantine" / sample_id / "uploaded_skill"


def _stage23_passed(stage23_summary: dict[str, Any], sample_name: str) -> bool:
    per_sample = stage23_summary.get("per_sample", {}).get(sample_name, {})
    return bool(per_sample.get("all_rounds_runtime_boundary_passed") is True)


def _safe_stem(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name)
