#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_UI_ROOT = REPO_ROOT / "web_ui"
if str(WEB_UI_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_UI_ROOT))

import real_skill_intake


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 19 real skill intake static-only runner")
    parser.add_argument(
        "--inbox",
        default=str(real_skill_intake.INBOX_DIR),
        help="Directory containing manually supplied .zip, .tar.gz, or .tgz skill archives",
    )
    args = parser.parse_args()

    summary = real_skill_intake.run_inbox_static_only(args.inbox)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
