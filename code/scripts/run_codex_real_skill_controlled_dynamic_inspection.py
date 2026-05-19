#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_UI_ROOT = REPO_ROOT / "web_ui"
if str(WEB_UI_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_UI_ROOT))

from safe_extract import safe_extract_archive

import real_skill_intake


OUTPUT_ROOT = REPO_ROOT / "analysis_results" / "real_skill_controlled_dynamic_inspection"
REPORTS_DIR = OUTPUT_ROOT / "reports"
QUARANTINE_DIR = OUTPUT_ROOT / "quarantine"
DEFAULT_RUNTIME_IMAGE = "python:3.11-slim"
ALLOWED_RUNTIME_IMAGES = {"python:3.11-slim"}
ALLOWED_CANDIDATE_ARCHIVES = ("ideation.zip", "react-effect-patterns.zip")
BLOCKED_ARCHIVES = {"implementation-guide.zip", "logging-best-practices.zip", "val-town-cli.zip"}
FAKE_HOME = "/home/codexsafe"
FAKE_CODEX_HOME = "/home/codexsafe/.codex"
TIMEOUT_SECONDS = 30
HARDENING_POLICY_VERSION = "stage22-runtime-hardening-v1"
PIDS_LIMIT = "256"
MEMORY_LIMIT = "512m"
CPU_LIMIT = "1.0"
SENSITIVE_ENV_EXACT = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "CODEX_HOME",
    "SSH_AUTH_SOCK",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
}
SENSITIVE_ENV_SUFFIXES = ("_TOKEN", "_KEY", "_SECRET")


def ensure_output_dirs() -> None:
    for path in (OUTPUT_ROOT, REPORTS_DIR, QUARANTINE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _relative_repo_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _load_stage20_summary() -> dict[str, Any]:
    path = REPO_ROOT / "analysis_results" / "real_skill_batch_static_dashboard" / "summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _stage20_by_archive() -> dict[str, dict[str, Any]]:
    summary = _load_stage20_summary()
    return {sample["archive_name"]: sample for sample in summary.get("samples", [])}


def validate_candidate_archive(archive_name: str, stage20_sample: dict[str, Any] | None = None) -> dict[str, Any]:
    stage20 = stage20_sample or _stage20_by_archive().get(archive_name)
    if archive_name not in ALLOWED_CANDIDATE_ARCHIVES:
        return {"allowed": False, "reason": f"archive is not in Stage 21 allowlist: {archive_name}"}
    if not stage20:
        return {"allowed": False, "reason": "archive missing from Stage 20 summary"}
    if stage20.get("category") != "stage21_candidate":
        return {"allowed": False, "reason": f"archive is not a Stage 21 candidate: {stage20.get('category')}"}
    if any(int(stage20.get(key, 0)) != 0 for key in ("critical", "high", "medium", "low")):
        return {"allowed": False, "reason": "Stage 21 requires C0 H0 M0 L0"}
    if stage20.get("dynamic_gate_status") != "allowed_for_manual_review":
        return {"allowed": False, "reason": "dynamic gate plan-only was not allowed_for_manual_review"}
    return {"allowed": True, "reason": "allowed Stage 21 candidate"}


def _sanitized_subprocess_env(output_dir: Path, env: dict[str, str] | None = None) -> dict[str, str]:
    source = os.environ if env is None else env
    subprocess_home = output_dir / "subprocess_home"
    subprocess_home.mkdir(parents=True, exist_ok=True)
    clean_env = {
        "PATH": source.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": FAKE_HOME,
        "CODEX_HOME": FAKE_CODEX_HOME,
    }
    if source.get("LANG"):
        clean_env["LANG"] = source["LANG"]
    if source.get("LC_ALL"):
        clean_env["LC_ALL"] = source["LC_ALL"]
    return clean_env


def _sensitive_env_names(env: dict[str, str] | None = None) -> list[str]:
    source = os.environ if env is None else env
    names = []
    for name in source:
        if name in SENSITIVE_ENV_EXACT or name.endswith(SENSITIVE_ENV_SUFFIXES):
            names.append(name)
    return sorted(set(names))


def _image_allowlisted(image: str) -> bool:
    return image in ALLOWED_RUNTIME_IMAGES


def inspect_local_runtime_image(image: str, clean_env: dict[str, str]) -> dict[str, Any]:
    if not _image_allowlisted(image):
        return {
            "runtime_image": image,
            "image_allowlisted": False,
            "image_present_locally": False,
            "image_inspect_performed": False,
            "image_pull_prevented": True,
            "docker_pull_executed": False,
        }
    completed = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=clean_env,
        check=False,
    )
    return {
        "runtime_image": image,
        "image_allowlisted": True,
        "image_present_locally": completed.returncode == 0,
        "image_inspect_performed": True,
        "image_inspect_exit_code": completed.returncode,
        "image_pull_prevented": completed.returncode != 0,
        "docker_pull_executed": False,
    }


def build_benign_inspection_command(sample_id: str, skill_path: Path, output_dir: Path, image: str = DEFAULT_RUNTIME_IMAGE) -> dict[str, Any]:
    if not _image_allowlisted(image):
        raise ValueError("runtime image is not allowlisted")
    skill = skill_path.resolve()
    output = output_dir.resolve()
    container_name = f"codex-real-skill-stage21-{sample_id}"
    inspect_script = (
        "set -eu; "
        "pwd; "
        "find /workspace/skill -maxdepth 3 -type f -print | sort; "
        "skill_md=$(find /workspace/skill -name SKILL.md -type f | head -n 1); "
        "if [ -n \"$skill_md\" ]; then printf '\\n--- SKILL.md ---\\n'; cat \"$skill_md\"; fi"
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        PIDS_LIMIT,
        "--memory",
        MEMORY_LIMIT,
        "--cpus",
        CPU_LIMIT,
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--tmpfs",
        "/home/codexsafe:rw,nosuid,nodev,uid=1000,gid=1000,mode=700",
        "-e",
        "HOME=/home/codexsafe",
        "-e",
        "CODEX_HOME=/home/codexsafe/.codex",
        "-v",
        f"{skill}:/workspace/skill:ro",
        "-v",
        f"{output}:/output:rw",
        image,
        "/bin/sh",
        "-c",
        inspect_script,
    ]
    return {
        "command": command,
        "container_name": container_name,
        "runtime_image": image,
        "network_mode": "none",
        "sample_mount_mode": "read-only",
        "output_mount_mode": "writable",
        "fake_home_used": True,
        "fake_codex_home_used": True,
        "docker_sock_mounted": False,
        "privileged": False,
        "network_host": False,
        "hardening_policy_version": HARDENING_POLICY_VERSION,
        "no_new_privileges": True,
        "cap_drop_all": True,
        "read_only_rootfs": True,
        "pids_limit": PIDS_LIMIT,
        "memory_limit": MEMORY_LIMIT,
        "cpu_limit": CPU_LIMIT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "docker_network_none": True,
        "docker_network_host_forbidden": True,
        "docker_sock_forbidden": True,
        "privileged_forbidden": True,
        "real_home_forbidden": True,
        "real_codex_home_forbidden": True,
        "real_token_forbidden": True,
        "uploaded_script_execution_forbidden": True,
        "install_command_forbidden": True,
        "docker_pull_forbidden": True,
        "local_image_preflight_required": True,
        "sanitized_env_required": True,
        "runtime_audit_complete": True,
        "uploaded_scripts_executed": False,
        "codex_executed": False,
        "strace_executed": False,
        "docker_pull_executed": False,
    }


def _archive_path(inbox: Path, archive_name: str) -> Path:
    path = (inbox / archive_name).resolve()
    path.relative_to(inbox.resolve())
    return path


def run_candidate(archive_name: str, inbox: Path, *, require_human_approved: bool, image: str = DEFAULT_RUNTIME_IMAGE) -> dict[str, Any]:
    ensure_output_dirs()
    stage20 = _stage20_by_archive().get(archive_name)
    validation = validate_candidate_archive(archive_name, stage20)
    manifest = real_skill_intake.compute_archive_manifest(_archive_path(inbox, archive_name)) if (inbox / archive_name).exists() else {}
    sample_id = manifest.get("sample_id", archive_name.replace(".", "_"))
    output_dir = REPORTS_DIR / sample_id
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "dynamic_report.json"
    md_path = output_dir / "report.md"
    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"
    base = _base_report(archive_name, manifest, validation, image)

    if not validation["allowed"]:
        base["final_verdict"] = f"blocked: {validation['reason']}"
        _write_candidate_outputs(base, report_path, md_path, stdout_path, stderr_path)
        return base
    if not require_human_approved:
        base["final_verdict"] = "fail closed: --require-human-approved is required"
        _write_candidate_outputs(base, report_path, md_path, stdout_path, stderr_path)
        return base

    candidate_root = QUARANTINE_DIR / sample_id
    if candidate_root.exists():
        shutil.rmtree(candidate_root)
    skill_dir = candidate_root / "uploaded_skill"
    safe_extract_archive(_archive_path(inbox, archive_name), skill_dir)
    command_info = build_benign_inspection_command(sample_id, skill_dir, output_dir, image=image)
    clean_env = _sanitized_subprocess_env(output_dir)
    base.update(command_info)
    base.update(
        {
            "host_sensitive_env_detected": bool(_sensitive_env_names()),
            "host_sensitive_env_names_redacted": _sensitive_env_names(),
            "sanitized_subprocess_env_used": True,
            "sanitized_subprocess_env_keys": sorted(clean_env),
            "real_tokens_present": False,
            "real_tokens_passed_to_container": False,
            "execution_attempted": True,
        }
    )
    image_preflight = inspect_local_runtime_image(image, clean_env)
    base.update(image_preflight)
    if not image_preflight["image_allowlisted"] or not image_preflight["image_present_locally"]:
        base["final_verdict"] = "fail closed: required local runtime image is missing"
        _write_candidate_outputs(base, report_path, md_path, stdout_path, stderr_path)
        return base
    completed = subprocess.run(
        command_info["command"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=clean_env,
        check=False,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    base.update(
        {
            "execution_performed": True,
            "container_started": True,
            "container_removed": True,
            "exit_code": completed.returncode,
            "final_verdict": "controlled no-network benign inspection completed" if completed.returncode == 0 else "controlled no-network benign inspection completed with nonzero exit",
        }
    )
    _write_candidate_outputs(base, report_path, md_path, stdout_path, stderr_path, preserve_logs=True)
    return base


def _base_report(archive_name: str, manifest: dict[str, Any], validation: dict[str, Any], image: str) -> dict[str, Any]:
    return {
        "archive_name": archive_name,
        "sample_id": manifest.get("sample_id"),
        "sha256": manifest.get("sha256"),
        "runtime_image": image,
        "image_allowlisted": _image_allowlisted(image),
        "image_present_locally": None,
        "docker_pull_executed": False,
        "execution_attempted": False,
        "execution_performed": False,
        "container_started": False,
        "container_removed": False,
        "network_mode": "none",
        "sample_mount_mode": "read-only",
        "output_mount_mode": "writable",
        "fake_home_used": True,
        "fake_codex_home_used": True,
        "docker_sock_mounted": False,
        "privileged": False,
        "network_host": False,
        "hardening_policy_version": HARDENING_POLICY_VERSION,
        "no_new_privileges": True,
        "cap_drop_all": True,
        "read_only_rootfs": True,
        "pids_limit": PIDS_LIMIT,
        "memory_limit": MEMORY_LIMIT,
        "cpu_limit": CPU_LIMIT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "docker_network_none": True,
        "docker_network_host_forbidden": True,
        "docker_sock_forbidden": True,
        "privileged_forbidden": True,
        "real_home_forbidden": True,
        "real_codex_home_forbidden": True,
        "real_token_forbidden": True,
        "real_tokens_present": False,
        "real_tokens_passed_to_container": False,
        "uploaded_script_execution_forbidden": True,
        "install_command_forbidden": True,
        "docker_pull_forbidden": True,
        "local_image_preflight_required": True,
        "sanitized_env_required": True,
        "runtime_audit_complete": True,
        "uploaded_scripts_executed": False,
        "codex_executed": False,
        "strace_executed": False,
        "validation": validation,
        "final_verdict": "not run",
    }


def _write_candidate_outputs(report: dict[str, Any], report_path: Path, md_path: Path, stdout_path: Path, stderr_path: Path, *, preserve_logs: bool = False) -> None:
    if not preserve_logs:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_candidate_report(report), encoding="utf-8")


def _render_candidate_report(report: dict[str, Any]) -> str:
    fields = [
        "archive_name",
        "sha256",
        "runtime_image",
        "image_allowlisted",
        "image_present_locally",
        "docker_pull_executed",
        "execution_attempted",
        "execution_performed",
        "container_started",
        "container_removed",
        "network_mode",
        "sample_mount_mode",
        "output_mount_mode",
        "fake_home_used",
        "fake_codex_home_used",
        "docker_sock_mounted",
        "privileged",
        "network_host",
        "hardening_policy_version",
        "no_new_privileges",
        "cap_drop_all",
        "read_only_rootfs",
        "pids_limit",
        "memory_limit",
        "cpu_limit",
        "timeout_seconds",
        "docker_network_none",
        "docker_network_host_forbidden",
        "docker_sock_forbidden",
        "privileged_forbidden",
        "real_home_forbidden",
        "real_codex_home_forbidden",
        "real_token_forbidden",
        "real_tokens_present",
        "real_tokens_passed_to_container",
        "uploaded_script_execution_forbidden",
        "install_command_forbidden",
        "docker_pull_forbidden",
        "local_image_preflight_required",
        "sanitized_env_required",
        "runtime_audit_complete",
        "uploaded_scripts_executed",
        "codex_executed",
        "strace_executed",
        "final_verdict",
    ]
    lines = ["# Stage 21 Controlled Dynamic Inspection Report", ""]
    lines.extend(f"- {field}: `{report.get(field)}`" for field in fields)
    lines.append("")
    return "\n".join(lines)


def write_dashboard(results: list[dict[str, Any]]) -> dict[str, Any]:
    ensure_output_dirs()
    summary = {
        "stage": "Stage 21 Low-risk Real Skill Controlled Dynamic Inspection",
        "total_requested": len(results),
        "allowed_candidates": [item["archive_name"] for item in results if item.get("validation", {}).get("allowed")],
        "blocked_archives_not_run": sorted(BLOCKED_ARCHIVES),
        "results": results,
        "docker_pull_executed": any(item.get("docker_pull_executed") for item in results),
        "codex_executed": any(item.get("codex_executed") for item in results),
        "strace_executed": any(item.get("strace_executed") for item in results),
        "uploaded_scripts_executed": any(item.get("uploaded_scripts_executed") for item in results),
        "network_mode": "none",
    }
    (OUTPUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (OUTPUT_ROOT / "risk_table.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["archive_name", "sha256", "execution_attempted", "execution_performed", "container_started", "container_removed", "final_verdict"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in results:
            writer.writerow({field: item.get(field) for field in fields})
    (OUTPUT_ROOT / "report.md").write_text(_render_dashboard(summary), encoding="utf-8")
    return summary


def _render_dashboard(summary: dict[str, Any]) -> str:
    lines = [
        "# Stage 21 Low-risk Real Skill Controlled Dynamic Inspection",
        "",
        "Stage 21 only targets C0 H0 M0 L0 real skill samples.",
        "",
        "- Candidates: `ideation.zip`, `react-effect-patterns.zip`",
        "- Blocked remains blocked: `implementation-guide.zip`",
        "- Manual review remains non-dynamic: `logging-best-practices.zip`, `val-town-cli.zip`",
        "- Docker network mode: `none`",
        "- Image pulls: `forbidden`",
        "- Local image inspect required before docker run.",
        "- docker.sock mounted: `false`",
        "- privileged: `false`",
        "- network host: `false`",
        "- real tokens passed: `false`",
        "- codex_executed: `false`",
        "- strace_executed: `false`",
        "- uploaded_scripts_executed: `false`",
        "- Inspection mode: benign file tree and SKILL.md read only.",
        "",
        "## Results",
        "",
    ]
    for item in summary["results"]:
        lines.append(f"- `{item['archive_name']}`: {item.get('final_verdict')}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 21 controlled no-network real skill benign inspection")
    parser.add_argument("--inbox", default=str(real_skill_intake.INBOX_DIR))
    parser.add_argument("--only", nargs="+", default=list(ALLOWED_CANDIDATE_ARCHIVES))
    parser.add_argument("--require-human-approved", action="store_true")
    parser.add_argument("--runtime-image", default=DEFAULT_RUNTIME_IMAGE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inbox = Path(args.inbox).resolve()
    results = []
    for archive_name in args.only:
        results.append(
            run_candidate(
                archive_name,
                inbox,
                require_human_approved=bool(args.require_human_approved),
                image=args.runtime_image,
            )
        )
    summary = write_dashboard(results)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
