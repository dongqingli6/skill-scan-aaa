#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROLLED_ACTIVATION_ROOT = REPO_ROOT / "code" / "platforms" / "codex" / "controlled_activation"
if str(CONTROLLED_ACTIVATION_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROLLED_ACTIVATION_ROOT))

import activation_runner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Big Stage 25 controlled skill activation")
    parser.add_argument("--inbox", default="analysis_results/real_skill_intake/inbox")
    parser.add_argument("--only", nargs="+", required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--require-human-approved", action="store_true")
    parser.add_argument("--max-commands-per-sample", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.plan_only and not args.require_human_approved:
        raise SystemExit("fail closed: activation requires --require-human-approved")
    summary = activation_runner.run_controlled_activation_plan(
        inbox=Path(args.inbox).resolve(),
        sample_names=list(args.only),
        plan_only=bool(args.plan_only),
        require_human_approved=bool(args.require_human_approved),
        max_commands_per_sample=int(args.max_commands_per_sample),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
