#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = REPO_ROOT / "code" / "platforms" / "codex" / "doc_behavior_diff"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import divergence_analyzer
import divergence_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Big Stage 26 document-behavior divergence analysis")
    parser.add_argument("--inbox", default="analysis_results/real_skill_intake/inbox")
    parser.add_argument("--include-all-real-skills", action="store_true")
    parser.add_argument("--only", nargs="*")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.include_all_real_skills:
        sample_names = list(divergence_analyzer.DEFAULT_REAL_SKILLS)
    elif args.only:
        sample_names = list(args.only)
    else:
        sample_names = list(divergence_analyzer.DEFAULT_REAL_SKILLS)
    summary = divergence_analyzer.analyze_doc_behavior_divergence(
        repo_root=REPO_ROOT,
        inbox=(REPO_ROOT / args.inbox).resolve(),
        sample_names=sample_names,
    )
    divergence_report.write_reports(summary, REPO_ROOT / "analysis_results" / "doc_behavior_divergence")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
