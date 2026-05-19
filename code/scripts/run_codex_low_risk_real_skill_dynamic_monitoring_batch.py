#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "code" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_codex_real_skill_controlled_dynamic_inspection as stage21


OUTPUT_ROOT = REPO_ROOT / "analysis_results" / "real_skill_dynamic_monitoring_batch"
RUNS_DIR = OUTPUT_ROOT / "runs"
ALLOWED_CANDIDATE_ARCHIVES = ("ideation.zip", "react-effect-patterns.zip")
BLOCKED_ARCHIVES = {"implementation-guide.zip", "logging-best-practices.zip", "val-town-cli.zip"}
DEFAULT_REPEAT = 2


def ensure_output_dirs() -> None:
    for path in (OUTPUT_ROOT, RUNS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _safe_name(archive_name: str) -> str:
    return archive_name.replace("/", "_").replace(".", "_")


def _load_stage20_by_archive() -> dict[str, dict[str, Any]]:
    return stage21._stage20_by_archive()


def _load_stage21_summary() -> dict[str, Any]:
    path = REPO_ROOT / "analysis_results" / "real_skill_controlled_dynamic_inspection" / "summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def validate_monitoring_candidate(archive_name: str, stage20_sample: dict[str, Any] | None = None) -> dict[str, Any]:
    stage20 = stage20_sample or _load_stage20_by_archive().get(archive_name)
    if archive_name not in ALLOWED_CANDIDATE_ARCHIVES:
        return {"allowed": False, "reason": f"archive is not in Stage 23 allowlist: {archive_name}"}
    if not stage20:
        return {"allowed": False, "reason": "archive missing from Stage 20 summary"}
    if stage20.get("category") != "stage21_candidate":
        return {"allowed": False, "reason": f"archive is not a low-risk dynamic monitoring candidate: {stage20.get('category')}"}
    if any(int(stage20.get(key, 0)) != 0 for key in ("critical", "high", "medium", "low")):
        return {"allowed": False, "reason": "Stage 23 requires C0 H0 M0 L0"}
    if stage20.get("dynamic_gate_status") != "allowed_for_manual_review":
        return {"allowed": False, "reason": "dynamic gate plan-only was not allowed_for_manual_review"}
    return {"allowed": True, "reason": "allowed Stage 23 low-risk monitoring candidate"}


def build_monitoring_command(sample_id: str, skill_path: Path, output_dir: Path, image: str = stage21.DEFAULT_RUNTIME_IMAGE) -> dict[str, Any]:
    return stage21.build_benign_inspection_command(sample_id, skill_path, output_dir, image=image)


def _configure_stage21_output(run_root: Path) -> None:
    stage21.OUTPUT_ROOT = run_root
    stage21.REPORTS_DIR = run_root / "reports"
    stage21.QUARANTINE_DIR = run_root / "quarantine"


def run_monitoring_round(
    archive_name: str,
    inbox: Path,
    *,
    round_number: int,
    require_human_approved: bool,
    image: str = stage21.DEFAULT_RUNTIME_IMAGE,
) -> dict[str, Any]:
    run_root = RUNS_DIR / _safe_name(archive_name) / f"round_{round_number}"
    _configure_stage21_output(run_root)
    result = stage21.run_candidate(
        archive_name,
        inbox,
        require_human_approved=require_human_approved,
        image=image,
    )
    result["monitoring_round"] = round_number
    try:
        result["stage23_output_root"] = str(run_root.relative_to(REPO_ROOT))
    except ValueError:
        result["stage23_output_root"] = str(run_root)
    return result


def _result_passed_runtime_boundary(result: dict[str, Any]) -> bool:
    expected = {
        "execution_performed": True,
        "container_started": True,
        "container_removed": True,
        "docker_pull_executed": False,
        "docker_sock_mounted": False,
        "privileged": False,
        "network_host": False,
        "real_tokens_passed_to_container": False,
        "uploaded_scripts_executed": False,
        "codex_executed": False,
        "strace_executed": False,
        "no_new_privileges": True,
        "cap_drop_all": True,
        "read_only_rootfs": True,
        "docker_network_none": True,
        "docker_network_host_forbidden": True,
        "docker_sock_forbidden": True,
        "privileged_forbidden": True,
        "sanitized_env_required": True,
        "runtime_audit_complete": True,
    }
    return all(result.get(key) == value for key, value in expected.items()) and result.get("network_mode") == "none"


def run_batch(
    inbox: Path,
    archives: list[str],
    *,
    repeat: int,
    require_human_approved: bool,
    image: str = stage21.DEFAULT_RUNTIME_IMAGE,
) -> dict[str, Any]:
    ensure_output_dirs()
    stage20_by_archive = _load_stage20_by_archive()
    stage21_summary = _load_stage21_summary()
    results: list[dict[str, Any]] = []
    validations: dict[str, dict[str, Any]] = {}

    for archive_name in archives:
        validation = validate_monitoring_candidate(archive_name, stage20_by_archive.get(archive_name))
        validations[archive_name] = validation
        if not validation["allowed"]:
            results.append(
                {
                    "archive_name": archive_name,
                    "monitoring_round": None,
                    "execution_attempted": False,
                    "execution_performed": False,
                    "container_started": False,
                    "container_removed": False,
                    "docker_pull_executed": False,
                    "uploaded_scripts_executed": False,
                    "codex_executed": False,
                    "strace_executed": False,
                    "validation": validation,
                    "final_verdict": f"blocked: {validation['reason']}",
                }
            )
            continue
        for round_number in range(1, repeat + 1):
            results.append(
                run_monitoring_round(
                    archive_name,
                    inbox,
                    round_number=round_number,
                    require_human_approved=require_human_approved,
                    image=image,
                )
            )

    summary = build_summary(results, validations, stage21_summary, repeat)
    write_outputs(summary)
    return summary


def build_summary(
    results: list[dict[str, Any]],
    validations: dict[str, dict[str, Any]],
    stage21_summary: dict[str, Any],
    repeat: int,
) -> dict[str, Any]:
    per_sample: dict[str, dict[str, Any]] = {}
    for archive_name in ALLOWED_CANDIDATE_ARCHIVES:
        sample_results = [item for item in results if item.get("archive_name") == archive_name]
        round_results = [item for item in sample_results if item.get("monitoring_round")]
        per_sample[archive_name] = {
            "validation": validations.get(archive_name, {}),
            "rounds_requested": repeat,
            "rounds_completed": sum(1 for item in round_results if item.get("execution_performed") is True),
            "all_rounds_runtime_boundary_passed": bool(round_results) and all(_result_passed_runtime_boundary(item) for item in round_results),
            "final_verdicts": [item.get("final_verdict") for item in round_results],
            "container_started_values": [item.get("container_started") for item in round_results],
            "container_removed_values": [item.get("container_removed") for item in round_results],
            "network_modes": sorted({str(item.get("network_mode")) for item in round_results}),
        }
    return {
        "stage": "Stage 23 Low-risk Real Skill Dynamic Monitoring Batch / Repeatability",
        "allowed_candidates": list(ALLOWED_CANDIDATE_ARCHIVES),
        "blocked_archives_not_run": sorted(BLOCKED_ARCHIVES),
        "repeat": repeat,
        "total_round_results": len([item for item in results if item.get("monitoring_round")]),
        "results": results,
        "per_sample": per_sample,
        "stage21_summary_present": bool(stage21_summary),
        "docker_pull_executed": any(item.get("docker_pull_executed") for item in results),
        "codex_executed": any(item.get("codex_executed") for item in results),
        "strace_executed": any(item.get("strace_executed") for item in results),
        "uploaded_scripts_executed": any(item.get("uploaded_scripts_executed") for item in results),
        "real_tokens_passed_to_container": any(item.get("real_tokens_passed_to_container") for item in results),
        "network_mode": "none",
        "final_verdict": "waiting for approved monitoring run" if not results else "batch monitoring summary generated",
    }


def write_outputs(summary: dict[str, Any]) -> None:
    ensure_output_dirs()
    (OUTPUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (OUTPUT_ROOT / "risk_table.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "archive_name",
            "monitoring_round",
            "execution_performed",
            "container_started",
            "container_removed",
            "network_mode",
            "docker_pull_executed",
            "uploaded_scripts_executed",
            "codex_executed",
            "strace_executed",
            "final_verdict",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in summary["results"]:
            writer.writerow({field: item.get(field) for field in fields})
    (OUTPUT_ROOT / "report.md").write_text(render_report(summary), encoding="utf-8")
    (OUTPUT_ROOT / "repeatability_report.md").write_text(render_repeatability(summary), encoding="utf-8")


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Stage 23 Low-risk Real Skill Dynamic Monitoring Batch / Repeatability",
        "",
        "Stage 23 only targets C0 H0 M0 L0 real skill samples.",
        "",
        "- Allowed candidates: `ideation.zip`, `react-effect-patterns.zip`",
        "- Blocked and not run: `implementation-guide.zip`, `logging-best-practices.zip`, `val-town-cli.zip`",
        "- Docker network mode: `none`",
        "- Image pull: `forbidden`",
        "- Local image inspect required before runtime.",
        "- docker.sock mounted: `false`",
        "- privileged: `false`",
        "- network host: `false`",
        "- real tokens passed: `false`",
        "- codex_executed: `false`",
        "- strace_executed: `false`",
        "- uploaded_scripts_executed: `false`",
        "- Monitoring mode: benign file tree, SKILL.md, metadata, and runtime audit fields only.",
        "",
        "## Results",
        "",
    ]
    for item in summary["results"]:
        lines.append(f"- `{item.get('archive_name')}` round `{item.get('monitoring_round')}`: {item.get('final_verdict')}")
    lines.append("")
    return "\n".join(lines)


def render_repeatability(summary: dict[str, Any]) -> str:
    lines = ["# Stage 23 Repeatability Report", ""]
    for archive_name, item in summary["per_sample"].items():
        lines.extend(
            [
                f"## {archive_name}",
                "",
                f"- rounds_requested: `{item.get('rounds_requested')}`",
                f"- rounds_completed: `{item.get('rounds_completed')}`",
                f"- all_rounds_runtime_boundary_passed: `{str(item.get('all_rounds_runtime_boundary_passed')).lower()}`",
                f"- network_modes: `{', '.join(item.get('network_modes') or [])}`",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 23 low-risk real skill dynamic monitoring batch")
    parser.add_argument("--inbox", default=str(stage21.real_skill_intake.INBOX_DIR))
    parser.add_argument("--only", nargs="+", default=list(ALLOWED_CANDIDATE_ARCHIVES))
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT)
    parser.add_argument("--require-human-approved", action="store_true")
    parser.add_argument("--runtime-image", default=stage21.DEFAULT_RUNTIME_IMAGE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1")
    if not args.require_human_approved:
        raise SystemExit("fail closed: --require-human-approved is required")
    summary = run_batch(
        Path(args.inbox).resolve(),
        list(args.only),
        repeat=args.repeat,
        require_human_approved=bool(args.require_human_approved),
        image=args.runtime_image,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
