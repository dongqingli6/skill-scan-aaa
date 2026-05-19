#!/usr/bin/env bash
set -euo pipefail

# Stage 19 real skill intake static-only test.
# This test uses synthetic archives and does not run Docker, Codex, strace,
# uploaded scripts, real skills, network commands, or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import json
import shutil
import stat
import sys
import tarfile
import zipfile
from io import BytesIO
from pathlib import Path

repo = Path.cwd()
web_ui = repo / "web_ui"
sys.path.insert(0, str(web_ui))

import real_skill_intake
from safe_extract import SafeExtractError


module_path = web_ui / "real_skill_intake.py"
runner_path = repo / "code" / "scripts" / "run_codex_real_skill_intake_static_only.py"
assert module_path.exists(), "real_skill_intake.py missing"
assert runner_path.exists(), "real skill intake CLI missing"

for path in [
    real_skill_intake.INTAKE_ROOT,
    real_skill_intake.INBOX_DIR,
    real_skill_intake.QUARANTINE_DIR,
    real_skill_intake.REPORTS_DIR,
    real_skill_intake.MANIFESTS_DIR,
]:
    resolved = path.resolve()
    resolved.relative_to((repo / "analysis_results" / "real_skill_intake").resolve())

for source_path in [module_path, runner_path]:
    text = source_path.read_text(encoding="utf-8")
    assert "shell=True" not in text, f"shell=True forbidden in {source_path}"
    assert "docker run" not in text.lower(), f"docker run forbidden in {source_path}"
    assert "codex exec" not in text.lower(), f"codex exec forbidden in {source_path}"
    for forbidden in ["subprocess.run", "docker run", "codex exec", "strace "]:
        assert forbidden not in text.lower(), f"{forbidden} forbidden in {source_path}"
    tree = ast.parse(text, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval forbidden in {source_path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True forbidden in {source_path}")

real_skill_intake.ensure_intake_dirs()
test_names = [
    "stage19_clean_test.zip",
    "stage19_dangerous_test.zip",
    "stage19_traversal_test.zip",
    "stage19_symlink_test.tar.gz",
]
for root in [real_skill_intake.QUARANTINE_DIR, real_skill_intake.REPORTS_DIR]:
    for child in root.glob("stage19_*_test_*"):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
for child in real_skill_intake.MANIFESTS_DIR.glob("stage19_*_test_*.json"):
    child.unlink()
for name in test_names:
    candidate = real_skill_intake.INBOX_DIR / name
    if candidate.exists():
        candidate.unlink()

clean_archive = real_skill_intake.INBOX_DIR / "stage19_clean_test.zip"
danger_archive = real_skill_intake.INBOX_DIR / "stage19_dangerous_test.zip"
traversal_archive = real_skill_intake.INBOX_DIR / "stage19_traversal_test.zip"
symlink_archive = real_skill_intake.INBOX_DIR / "stage19_symlink_test.tar.gz"

with zipfile.ZipFile(clean_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("SKILL.md", "# Clean Skill\nThis is a benign static-only test skill.\n")

with zipfile.ZipFile(danger_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr(
        "SKILL.md",
        "# Dangerous Text Skill\n"
        "docker.sock\n/var/run/docker.sock\nOPENAI_API_KEY\nGITHUB_TOKEN\n"
        "SSH_AUTH_SOCK\n~/.ssh/id_rsa\ncurl\nwget\ncredential\n",
    )

with zipfile.ZipFile(traversal_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("../SKILL.md", "# traversal\n")

with tarfile.open(symlink_archive, "w:gz") as archive:
    info = tarfile.TarInfo("SKILL.md")
    payload = b"# Symlink test\n"
    info.size = len(payload)
    archive.addfile(info, BytesIO(payload))
    link = tarfile.TarInfo("linked_secret")
    link.type = tarfile.SYMTYPE
    link.linkname = "/tmp/secret"
    archive.addfile(link)

manifest = real_skill_intake.compute_archive_manifest(clean_archive)
assert manifest["archive_name"] == clean_archive.name, manifest
assert len(manifest["sha256"]) == 64, manifest
assert manifest["size_bytes"] > 0, manifest
assert manifest["extension"] == ".zip", manifest

extract_info = real_skill_intake.safe_extract_real_skill(clean_archive, real_skill_intake.QUARANTINE_DIR)
extracted = Path(extract_info["extracted_path"])
assert extracted.is_dir(), extract_info
summary = real_skill_intake.summarize_extracted_skill(extracted)
assert summary["file_count"] == 1, summary
assert summary["has_skill_md"] is True, summary
assert summary["file_tree"] == ["SKILL.md"], summary

try:
    real_skill_intake.safe_extract_real_skill(traversal_archive, real_skill_intake.QUARANTINE_DIR)
    raise AssertionError("path traversal archive should be rejected")
except SafeExtractError:
    pass

try:
    real_skill_intake.safe_extract_real_skill(symlink_archive, real_skill_intake.QUARANTINE_DIR)
    raise AssertionError("symlink archive should be rejected")
except SafeExtractError:
    pass

danger_result = real_skill_intake.run_real_skill_static_only(danger_archive)
danger_risk = danger_result["static_report"]["risk_summary"]
assert int(danger_risk.get("critical", 0)) > 0 or int(danger_risk.get("high", 0)) > 0, danger_risk
danger_gate = danger_result["dynamic_gate_plan"]
assert danger_gate["eligibility"]["eligibility_status"] == "denied", danger_gate
assert danger_gate["execution_performed"] is False, danger_gate
assert danger_gate["container_started"] is False, danger_gate
assert danger_gate["uploaded_scripts_executed"] is False, danger_gate
assert danger_gate["codex_executed"] is False, danger_gate
assert danger_gate["strace_executed"] is False, danger_gate

inbox_archives = real_skill_intake.discover_real_skill_archives(real_skill_intake.INBOX_DIR)
assert clean_archive in inbox_archives and danger_archive in inbox_archives, inbox_archives
summary_result = real_skill_intake.run_inbox_static_only(real_skill_intake.INBOX_DIR)
assert summary_result["processed"] >= 2, summary_result
assert summary_result["docker_executed"] is False, summary_result
assert summary_result["codex_executed"] is False, summary_result
assert summary_result["strace_executed"] is False, summary_result
assert summary_result["real_skills_executed"] is False, summary_result
summary_json = real_skill_intake.REPORTS_DIR / "summary.json"
report_md = real_skill_intake.REPORTS_DIR / "report.md"
assert summary_json.exists(), "summary.json missing"
assert report_md.exists(), "report.md missing"
loaded = json.loads(summary_json.read_text(encoding="utf-8"))
assert loaded["network_enabled"] is False, loaded

for archive in [clean_archive, danger_archive, traversal_archive, symlink_archive]:
    if archive.exists():
        archive.unlink()
for root in [real_skill_intake.QUARANTINE_DIR, real_skill_intake.REPORTS_DIR]:
    for child in root.glob("stage19_*_test_*"):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
for child in real_skill_intake.MANIFESTS_DIR.glob("stage19_*_test_*.json"):
    child.unlink()

print("Codex real skill intake static-only test passed.")
PY

python3 code/scripts/run_codex_real_skill_intake_static_only.py --inbox analysis_results/real_skill_intake/inbox >/tmp/codex_real_skill_intake_cli_test.json

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

summary = json.loads(Path("analysis_results/real_skill_intake/reports/summary.json").read_text(encoding="utf-8"))
assert "processed" in summary, summary
assert summary["docker_executed"] is False, summary
assert summary["codex_executed"] is False, summary
assert summary["strace_executed"] is False, summary
assert summary["real_skills_executed"] is False, summary
assert Path("analysis_results/real_skill_intake/reports/report.md").exists()
print("Codex real skill intake CLI static-only test passed.")
PY

echo "Codex real skill intake static-only test passed."
