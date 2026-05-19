#!/usr/bin/env bash
set -euo pipefail

# Synthetic false-positive reduction test only.
# No Docker, Codex, strace, samples, network, real HOME, or real token reads.

python3 - <<'PY'
from __future__ import annotations

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
        "note": "synthetic false-positive test",
        "status": "extracted",
        "created_at": created,
        "updated_at": created,
        "uploaded_archive": None,
        "extracted_skill_path": str(root),
        "static_scan_status": "not_started",
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
clean_dir = base / "stage14_clean_synthetic" / "uploaded_skill"
danger_dir = base / "stage14_danger_synthetic" / "uploaded_skill"
for root in [clean_dir.parent, danger_dir.parent]:
    if root.exists():
        shutil.rmtree(root)

clean_dir.mkdir(parents=True)
(clean_dir / "SKILL.md").write_text(
    "\n".join(
        [
            "# Clean Synthetic Skill",
            "This skill does not use docker.sock.",
            "It does not access ~/.ssh.",
            "It uses no real token.",
            "It does not use --" + "privileged.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

clean_job = backend_adapter.run_static_scan(make_job("stage14_clean_synthetic", "clean", clean_dir))
assert clean_job["risk_summary"]["critical"] == 0, clean_job["risk_summary"]
assert clean_job["risk_summary"]["high"] == 0, clean_job["risk_summary"]
clean_report = Path(clean_job["report_paths"]["static_scan_report_json"]).read_text(encoding="utf-8")
assert '"suppressed": true' in clean_report, clean_report
assert "Suppressed documentation-only match" in Path(clean_job["report_paths"]["static_scan_report_md"]).read_text(encoding="utf-8")

danger_dir.mkdir(parents=True)
(danger_dir / "SKILL.md").write_text(
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

danger_job = backend_adapter.run_static_scan(make_job("stage14_danger_synthetic", "danger", danger_dir))
assert danger_job["risk_summary"]["critical"] > 0 or danger_job["risk_summary"]["high"] > 0, danger_job["risk_summary"]

for root in [clean_dir.parent, danger_dir.parent]:
    if root.exists():
        shutil.rmtree(root)

print("Codex Web UI false-positive synthetic test passed.")
PY
