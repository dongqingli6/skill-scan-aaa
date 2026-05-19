#!/usr/bin/env bash
set -euo pipefail

# Synthetic Web UI real static scanner integration test only.
# No Docker, Codex, strace, samples, network, real HOME, or real token reads.

python3 - <<'PY'
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path("web_ui").resolve()))

import backend_adapter
import job_store


def make_job(job_id: str, skill_name: str, root: Path) -> dict:
    created = job_store.now_iso()
    return {
        "job_id": job_id,
        "skill_name": skill_name,
        "note": "synthetic real static scanner integration test",
        "status": "extracted",
        "created_at": created,
        "updated_at": created,
        "uploaded_archive": None,
        "extracted_skill_path": str(root),
        "static_scan_status": "not_started",
        "static_scanner_mode": "not_started",
        "static_scanner_fallback_used": False,
        "static_scanner_warnings": [],
        "static_scanner_errors": [],
        "dynamic_scan_status": "not_started",
        "risk_summary": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "informational": 0,
        },
        "report_paths": {},
        "safety_boundaries": ["synthetic test only", "plan-only"],
        "errors": [],
    }


base = job_store.JOBS_ROOT
benign_root = base / "stage15_benign_synthetic" / "uploaded_skill"
danger_root = base / "stage15_danger_synthetic" / "uploaded_skill"
for root in [benign_root.parent, danger_root.parent]:
    if root.exists():
        shutil.rmtree(root)

benign_root.mkdir(parents=True)
(benign_root / "SKILL.md").write_text(
    "# Benign Synthetic Skill\n\nThis skill summarizes local documentation only.\n",
    encoding="utf-8",
)

benign_job = backend_adapter.run_static_scan(make_job("stage15_benign_synthetic", "benign", benign_root))
static_json_path = Path(benign_job["report_paths"]["static_scan_report_json"])
static_md_path = Path(benign_job["report_paths"]["static_scan_report_md"])
assert static_json_path.exists(), static_json_path
assert static_md_path.exists(), static_md_path
report = json.loads(static_json_path.read_text(encoding="utf-8"))
for key in ["scanner_mode", "risk_summary", "findings", "files_scanned", "skill_found"]:
    assert key in report, f"missing {key}"
assert report["scanner_mode"] in {"real_static_scanner", "fallback_static_adapter"}
if report["scanner_mode"] == "fallback_static_adapter":
    assert benign_job["static_scanner_fallback_used"] is True

danger_root.mkdir(parents=True)
(danger_root / "SKILL.md").write_text(
    "\n".join(
        [
            "# Dangerous Synthetic Skill",
            "This skill may use docker.sock.",
            "It may access ~/.ssh/id_rsa.",
            "It may run with --" + "privileged.",
        ]
    )
    + "\n",
    encoding="utf-8",
)
danger_job = backend_adapter.run_static_scan(make_job("stage15_danger_synthetic", "danger", danger_root))
summary = danger_job["risk_summary"]
assert summary["critical"] > 0 or summary["high"] > 0, summary

for root in [benign_root.parent, danger_root.parent]:
    if root.exists():
        shutil.rmtree(root)

print("Codex Web UI real static scanner synthetic test passed.")
PY
