#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = REPO_ROOT / "code" / "platforms" / "codex" / "opensource_release"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import competition_pack_builder
import demo_materials_builder
import docs_builder
import github_readme_builder
import release_audit
import release_manifest
import sanitize_public_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build open source release and competition package")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--build-docs", action="store_true")
    parser.add_argument("--build-demo-materials", action="store_true")
    parser.add_argument("--build-competition-pack", action="store_true")
    parser.add_argument("--output", default="analysis_results/opensource_release")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = REPO_ROOT / args.output
    public_files: list[str] = []
    audit = {"findings": []}
    if args.audit:
        audit = release_audit.run_release_audit(REPO_ROOT, output_root)
    if args.sanitize:
        public_files.extend(sanitize_public_artifacts.build_public_artifacts(REPO_ROOT, REPO_ROOT / "public_artifacts")["public_artifacts"])
    if args.build_docs:
        public_files.append(github_readme_builder.write_readme(REPO_ROOT))
        public_files.extend(docs_builder.build_docs(REPO_ROOT))
    if args.build_demo_materials:
        public_files.extend(demo_materials_builder.build_demo_materials(REPO_ROOT))
    if args.build_competition_pack:
        public_files.extend(competition_pack_builder.build_competition_pack(REPO_ROOT))
    manifest = {
        "stage": "Big Stage 30 Open Source Release and Competition Submission Package",
        "public_files_generated": sorted(set(public_files)),
        "sensitive_files_excluded": [item["path"] for item in audit.get("findings", [])],
        "release_readiness_checklist": {
            "readme": (REPO_ROOT / "README.md").exists(),
            "docs": (REPO_ROOT / "docs").exists(),
            "demo": (REPO_ROOT / "demo").exists(),
            "competition_materials": (REPO_ROOT / "competition_materials").exists(),
            "public_artifacts": (REPO_ROOT / "public_artifacts").exists(),
        },
        "test_status": "static tests expected",
        "safe_regression_status": _safe_regression_status(),
        "known_limitations": ["research prototype", "not production system", "raw real skill archives excluded"],
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "network_enabled": False,
        "real_api_called": False,
        "files_deleted": False,
    }
    release_manifest.write_manifest(output_root, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _safe_regression_status() -> str:
    path = REPO_ROOT / "analysis_results" / "codex_safe_regression_static_only" / "summary.json"
    if not path.exists():
        return "missing"
    return "recorded"


if __name__ == "__main__":
    raise SystemExit(main())
