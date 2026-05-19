#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = REPO_ROOT / "code" / "platforms" / "codex" / "scaled_validation"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import dashboard_data
import report_builder
import scaled_evaluation_runner
import synthetic_corpus_builder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Big Stage 27 scaled validation report")
    parser.add_argument("--build-synthetic-corpus", action="store_true")
    parser.add_argument("--include-real-skills", action="store_true")
    parser.add_argument("--static-only", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.static_only:
        raise SystemExit("fail closed: Stage 27 supports static-only mode only")
    output_root = REPO_ROOT / "analysis_results" / "scaled_validation"
    if args.build_synthetic_corpus:
        synthetic_corpus_builder.build_synthetic_corpus(output_root / "synthetic_corpus")
    summary = scaled_evaluation_runner.run_scaled_evaluation(REPO_ROOT, include_real_skills=bool(args.include_real_skills))
    report_builder.write_scaled_validation_reports(summary, output_root)
    dashboard_data.write_dashboard_data(summary, output_root)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
