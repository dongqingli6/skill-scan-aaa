#!/usr/bin/env bash
set -euo pipefail

# Stage 18 dangerous synthetic block test.
# The generated archive contains only a text SKILL.md.
# This test does not run Docker, Codex, strace, uploaded scripts, samples, or network commands.

python3 - <<'PY'
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path("web_ui").resolve()))

import backend_adapter
import dynamic_gate
import job_store
from safe_extract import safe_extract_archive


def assert_false(value: object, field: str) -> None:
    assert value is False, f"{field} must be false, got {value!r}"


job = job_store.create_job("stage18_dangerous_synthetic", "Stage 18 dangerous synthetic block test")
job_root = job_store.job_dir(job["job_id"])
try:
    archive_dir = job_root / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / "dangerous_synthetic_skill.zip"
    skill_text = """# Dangerous Synthetic Skill

This is a static-only negative gate test fixture.
It intentionally includes dangerous strings as inert text:

- docker.sock
- /var/run/docker.sock
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GITHUB_TOKEN
- SSH_AUTH_SOCK
- ~/.ssh/id_rsa
- curl
- wget
- chmod +x
- bash script.sh
- exfiltrate
- credential

These strings are not commands for this test. The archive contains only this
text SKILL.md file, and the test must not execute uploaded content.
"""
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("SKILL.md", skill_text)

    extracted_path = job_root / "uploaded_skill"
    extract_result = safe_extract_archive(archive_path, extracted_path)
    assert extract_result.files == ["SKILL.md"], extract_result
    assert (extracted_path / "SKILL.md").is_file(), "SKILL.md was not extracted"
    assert len([path for path in extracted_path.rglob("*") if path.is_file()]) == 1, "archive must contain one text file"

    job["uploaded_archive"] = str(archive_path.relative_to(job_store.REPO_ROOT))
    job["extracted_skill_path"] = extract_result.extracted_path
    job["status"] = "extracted"
    job_store.save_job(job)

    job = backend_adapter.run_static_scan(job_store.load_job(job["job_id"]))
    risk_summary = job["risk_summary"]
    critical = int(risk_summary.get("critical", 0))
    high = int(risk_summary.get("high", 0))
    assert critical > 0 or high > 0, risk_summary

    job = backend_adapter.run_dynamic_scan_plan(job_store.load_job(job["job_id"]))
    eligibility = job["dynamic_eligibility"]
    assert eligibility["allowed"] is False, eligibility
    assert eligibility["eligibility_status"] == "denied", eligibility
    assert "HIGH or CRITICAL static findings block dynamic execution" == eligibility["reason"], eligibility
    blockers = eligibility["blockers"]
    assert any("HIGH / CRITICAL static findings block dynamic execution" in blocker for blocker in blockers), blockers

    confirmed = backend_adapter.confirm_dynamic_execution(job_store.load_job(job["job_id"]), "attempted override")
    assert confirmed["dynamic_user_confirmed"] is False, confirmed
    assert confirmed["confirmed_at"] is None, confirmed
    assert confirmed["confirmation_text"] == "", confirmed

    def forbidden_subprocess_run(*args, **kwargs):
        raise AssertionError("Docker subprocess must not run for denied dangerous synthetic skill")

    original_subprocess_run = backend_adapter.safe_dynamic_runner.subprocess.run
    backend_adapter.safe_dynamic_runner.subprocess.run = forbidden_subprocess_run
    try:
        result = backend_adapter.run_safe_dynamic_scan(job_store.load_job(job["job_id"]))
    finally:
        backend_adapter.safe_dynamic_runner.subprocess.run = original_subprocess_run

    report = result["dynamic_execution_report"]
    assert result["dynamic_scan_status"] == "blocked", result["dynamic_scan_status"]
    assert report["final_verdict"] == "fail closed: dynamic gate denied or human confirmation missing", report
    assert_false(report["execution_attempted"], "execution_attempted")
    assert_false(report["execution_performed"], "execution_performed")
    assert_false(report["container_started"], "container_started")
    assert_false(report["container_removed"], "container_removed")
    assert_false(report["uploaded_scripts_executed"], "uploaded_scripts_executed")
    assert_false(report["codex_executed"], "codex_executed")
    assert_false(report["strace_executed"], "strace_executed")
    assert_false(report["docker_pull_executed"], "docker_pull_executed")
    assert report["image_inspect_performed"] is False, report
    assert report["eligibility"]["allowed"] is False, report["eligibility"]

    report_path = job_store.REPO_ROOT / result["report_paths"]["dynamic_execution_report_json"]
    report_json = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_json["execution_performed"] is False, report_json
    assert report_json["container_started"] is False, report_json
    assert report_json["uploaded_scripts_executed"] is False, report_json
    assert report_json["codex_executed"] is False, report_json
    assert report_json["strace_executed"] is False, report_json

finally:
    if job_root.exists():
        shutil.rmtree(job_root)

print("Codex Web UI dangerous synthetic block test passed.")
PY

echo "Codex Web UI dangerous synthetic block test passed."
