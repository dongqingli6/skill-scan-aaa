#!/usr/bin/env bash
set -euo pipefail

# Stage 16 dynamic gate synthetic logic test.
# No Docker, Codex, strace, samples, network, real HOME, or real token reads.

python3 - <<'PY'
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from subprocess import CompletedProcess

sys.path.insert(0, str(Path("web_ui").resolve()))

import backend_adapter
import dynamic_gate
import job_store


def make_job(job_id: str, critical: int, high: int, *, safety_boundaries=None, required_controls=None) -> dict:
    root = job_store.JOBS_ROOT / job_id
    skill = root / "uploaded_skill"
    static_dir = root / "static_scan"
    if root.exists():
        shutil.rmtree(root)
    skill.mkdir(parents=True)
    static_dir.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Synthetic Skill\n", encoding="utf-8")
    static_report = {
        "scanner_mode": "synthetic",
        "risk_summary": {
            "critical": critical,
            "high": high,
            "medium": 0,
            "low": 0,
            "informational": 0,
        },
        "findings": [],
        "files_scanned": 1,
        "skill_found": True,
    }
    static_path = static_dir / "static_report.json"
    static_path.write_text(json.dumps(static_report, indent=2), encoding="utf-8")
    created = job_store.now_iso()
    job = {
        "job_id": job_id,
        "skill_name": job_id,
        "note": "synthetic dynamic gate test",
        "status": "static_completed",
        "created_at": created,
        "updated_at": created,
        "uploaded_archive": None,
        "extracted_skill_path": str(skill),
        "static_scan_status": "completed",
        "static_scanner_mode": "synthetic",
        "static_scanner_fallback_used": False,
        "static_scanner_warnings": [],
        "static_scanner_errors": [],
        "dynamic_scan_status": "not_started",
        "dynamic_plan_status": "not_started",
        "dynamic_user_confirmed": False,
        "confirmed_at": None,
        "confirmation_text": "",
        "dynamic_eligibility": {},
        "dynamic_execution_report": {},
        "risk_summary": static_report["risk_summary"],
        "report_paths": {"static_scan_report_json": str(static_path.relative_to(job_store.REPO_ROOT))},
        "safety_boundaries": safety_boundaries if safety_boundaries is not None else job_store.default_safety_boundaries(),
        "required_controls": required_controls or [],
        "errors": [],
    }
    job_store.save_job(job)
    return job


allowed_job = make_job("stage16_allowed_synthetic", 0, 0)
allowed = dynamic_gate.evaluate_dynamic_eligibility(allowed_job)
assert allowed["allowed"] is True, allowed
plan = dynamic_gate.build_safe_dynamic_plan(allowed_job)
for control in ["no_network", "fake_home", "fake_codex_home", "readonly_sample_mount", "output_rw", "no_docker_sock", "no_privileged", "no_network_host", "no_real_token", "runtime_monitor_required"]:
    assert control in plan["required_controls"], control
saved_allowed = job_store.load_job("stage16_allowed_synthetic")
assert saved_allowed["dynamic_plan_status"] == "ready", saved_allowed
assert saved_allowed["dynamic_plan_path"].endswith("dynamic_plan.json"), saved_allowed.get("dynamic_plan_path")
assert saved_allowed["safety_boundaries"]["fake_home"] is True, saved_allowed["safety_boundaries"]

original_subprocess_run = backend_adapter.safe_dynamic_runner.subprocess.run
backend_adapter.safe_dynamic_runner.subprocess.run = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Docker subprocess must not run while unconfirmed"))
unconfirmed = backend_adapter.run_safe_dynamic_scan(job_store.load_job("stage16_allowed_synthetic"))
backend_adapter.safe_dynamic_runner.subprocess.run = original_subprocess_run
assert unconfirmed["dynamic_scan_status"] == "blocked", unconfirmed["dynamic_scan_status"]
assert unconfirmed["dynamic_execution_report"]["execution_attempted"] is False
assert unconfirmed["dynamic_execution_report"]["execution_performed"] is False

confirmed = backend_adapter.confirm_dynamic_execution(job_store.load_job("stage16_allowed_synthetic"), "synthetic confirmation")
original = backend_adapter.safe_dynamic_runner.run_safe_dynamic_execution
backend_adapter.safe_dynamic_runner.run_safe_dynamic_execution = lambda job: original(job, dry_run=True)
try:
    confirmed = backend_adapter.run_safe_dynamic_scan(confirmed)
finally:
    backend_adapter.safe_dynamic_runner.run_safe_dynamic_execution = original
assert confirmed["dynamic_scan_status"] == "dry_run", confirmed["dynamic_scan_status"]
assert confirmed["dynamic_execution_report"]["execution_attempted"] is True
assert confirmed["dynamic_execution_report"]["execution_performed"] is False

sensitive_value = "redacted-test-value"
previous_env = {name: os.environ.get(name) for name in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "SSH_AUTH_SOCK", "CODEX_HOME"]}
os.environ["OPENAI_API_KEY"] = sensitive_value
os.environ["ANTHROPIC_API_KEY"] = "anthropic-redacted-test-value"
os.environ["GITHUB_TOKEN"] = "github-redacted-test-value"
os.environ["SSH_AUTH_SOCK"] = "ssh-auth-redacted-test-value"
os.environ["CODEX_HOME"] = "real-codex-home-redacted-test-value"
captured = {}

def fake_subprocess_run(command, **kwargs):
    captured.setdefault("commands", []).append(command)
    captured["command"] = command
    captured["env"] = kwargs["env"]
    return CompletedProcess(command, 0, stdout="synthetic benign inspection\n", stderr="")

confirmed = backend_adapter.confirm_dynamic_execution(job_store.load_job("stage16_allowed_synthetic"), "synthetic env confirmation")
original_subprocess_run = backend_adapter.safe_dynamic_runner.subprocess.run
backend_adapter.safe_dynamic_runner.subprocess.run = fake_subprocess_run
try:
    completed = backend_adapter.run_safe_dynamic_scan(confirmed)
finally:
    backend_adapter.safe_dynamic_runner.subprocess.run = original_subprocess_run
    for name, value in previous_env.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value

assert completed["dynamic_scan_status"] == "completed", completed["dynamic_scan_status"]
report = completed["dynamic_execution_report"]
assert captured["commands"][0][:3] == ["docker", "image", "inspect"], captured["commands"]
assert captured["commands"][1][:2] == ["docker", "run"], captured["commands"]
assert report["runtime_image"] == "python:3.11-slim", report
assert report["image_allowlisted"] is True, report
assert report["image_present_locally"] is True, report
assert report["image_pull_prevented"] is False, report
assert report["docker_pull_executed"] is False, report
assert report["host_sensitive_env_detected"] is True, report
assert "OPENAI_API_KEY" in report["host_sensitive_env_names_redacted"], report
assert sensitive_value not in json.dumps(report, sort_keys=True), report
assert report["sanitized_subprocess_env_used"] is True, report
assert report["real_tokens_passed_to_container"] is False, report
clean_env = captured["env"]
for forbidden_name in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "SSH_AUTH_SOCK"]:
    assert forbidden_name not in clean_env, clean_env
assert clean_env["CODEX_HOME"] == "/home/codexsafe/.codex", clean_env
assert clean_env["CODEX_HOME"] != "real-codex-home-redacted-test-value", clean_env
assert backend_adapter.safe_dynamic_runner._clean_env_has_sensitive_passthrough({"OPENAI_API_KEY": "redacted"}) is True
assert backend_adapter.safe_dynamic_runner._docker_command_has_sensitive_env_passthrough(["docker", "run", "-e", "OPENAI_API_KEY=redacted"]) is True
report_path = job_store.JOBS_ROOT / "stage16_allowed_synthetic" / "dynamic_execution" / "runtime_execution_report.json"
report_text = report_path.read_text(encoding="utf-8")
assert sensitive_value not in report_text, report_text
report_md = job_store.JOBS_ROOT / "stage16_allowed_synthetic" / "dynamic_execution" / "report.md"
assert sensitive_value not in report_md.read_text(encoding="utf-8")

image_missing_job = make_job("stage16_image_missing_synthetic", 0, 0)
dynamic_gate.build_safe_dynamic_plan(image_missing_job)
image_missing_job = backend_adapter.confirm_dynamic_execution(job_store.load_job("stage16_image_missing_synthetic"), "synthetic image missing confirmation")
inspect_calls = []

def image_missing_subprocess_run(command, **kwargs):
    inspect_calls.append(command)
    if command[:3] == ["docker", "image", "inspect"]:
        return CompletedProcess(command, 1, stdout="", stderr="image not found")
    raise AssertionError("docker run must not execute when local runtime image is missing")

original_subprocess_run = backend_adapter.safe_dynamic_runner.subprocess.run
backend_adapter.safe_dynamic_runner.subprocess.run = image_missing_subprocess_run
try:
    image_missing_result = backend_adapter.run_safe_dynamic_scan(image_missing_job)
finally:
    backend_adapter.safe_dynamic_runner.subprocess.run = original_subprocess_run
assert inspect_calls and inspect_calls[0][:3] == ["docker", "image", "inspect"], inspect_calls
image_missing_report = image_missing_result["dynamic_execution_report"]
assert image_missing_result["dynamic_scan_status"] == "blocked", image_missing_result["dynamic_scan_status"]
assert image_missing_report["image_present_locally"] is False, image_missing_report
assert image_missing_report["image_pull_prevented"] is True, image_missing_report
assert image_missing_report["docker_pull_executed"] is False, image_missing_report
assert image_missing_report["execution_performed"] is False, image_missing_report
assert image_missing_report["container_started"] is False, image_missing_report
assert image_missing_report["final_verdict"] == "fail closed: required local runtime image is missing", image_missing_report

blocked_job = make_job("stage16_blocked_synthetic", 1, 0)
blocked = dynamic_gate.evaluate_dynamic_eligibility(blocked_job)
assert blocked["allowed"] is False, blocked
assert blocked["blockers"], blocked
assert any("critical static findings" in item for item in blocked["blockers"]), blocked["blockers"]

fake_home_false = job_store.default_safety_boundaries()
fake_home_false["fake_home"] = False
fake_home_job = make_job("stage16_fake_home_false_synthetic", 0, 0, safety_boundaries=fake_home_false)
fake_home_blocked = dynamic_gate.evaluate_dynamic_eligibility(fake_home_job)
assert fake_home_blocked["allowed"] is False, fake_home_blocked
assert any("fake_home" in item for item in fake_home_blocked["blockers"]), fake_home_blocked["blockers"]

missing_boundaries_job = make_job(
    "stage16_missing_boundaries_synthetic",
    0,
    0,
    safety_boundaries=None,
    required_controls=list(dynamic_gate.REQUIRED_CONTROLS),
)
missing_boundaries_job.pop("safety_boundaries")
missing_boundaries_job["required_controls"] = list(dynamic_gate.REQUIRED_CONTROLS)
job_store.save_job(missing_boundaries_job)
normalized = dynamic_gate.evaluate_dynamic_eligibility(job_store.load_job("stage16_missing_boundaries_synthetic"))
assert normalized["allowed"] is True, normalized
plan = dynamic_gate.build_safe_dynamic_plan(job_store.load_job("stage16_missing_boundaries_synthetic"))
assert plan["eligibility"]["allowed"] is True, plan
saved_normalized = job_store.load_job("stage16_missing_boundaries_synthetic")
assert saved_normalized["safety_boundaries"]["fake_home"] is True, saved_normalized["safety_boundaries"]

for job_id in [
    "stage16_allowed_synthetic",
    "stage16_blocked_synthetic",
    "stage16_fake_home_false_synthetic",
    "stage16_image_missing_synthetic",
    "stage16_missing_boundaries_synthetic",
]:
    root = job_store.JOBS_ROOT / job_id
    if root.exists():
        shutil.rmtree(root)

print("Codex Web UI dynamic gate synthetic test passed.")
PY
