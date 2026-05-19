#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = REPO_ROOT / "code" / "platforms" / "codex" / "human_review_labeling"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import evidence_collector
import labeling_report
import review_card_builder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Big Stage 29 human review labeling")
    parser.add_argument("--collect-stage-results", action="store_true")
    parser.add_argument("--include-real-skills", action="store_true")
    parser.add_argument("--include-synthetic", action="store_true")
    parser.add_argument("--output", default="analysis_results/human_review_labeling")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.collect_stage_results:
        raise SystemExit("fail closed: use --collect-stage-results to read existing evidence")
    bundle = evidence_collector.collect_evidence(
        REPO_ROOT,
        include_real=bool(args.include_real_skills),
        include_synthetic=bool(args.include_synthetic),
    )
    cards = [review_card_builder.build_review_card(item) for item in bundle["samples"]]
    summary = labeling_report.write_labeling_outputs(cards, REPO_ROOT / args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
