"""Write a plan for future filesystem diff collection. Does not execute it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_filesystem_diff_plan(output_dir: str | Path) -> dict:
    return {
        "plan_type": "filesystem_diff_plan",
        "execution_enabled": False,
        "before_snapshot": ["find /workspace /home/codexsafe /output -xdev -printf '%p\\t%y\\t%s\\t%T@\\n'"],
        "after_snapshot": ["find /workspace /home/codexsafe /output -xdev -printf '%p\\t%y\\t%s\\t%T@\\n'"],
        "allowed_writable_paths": ["/output", "/home/codexsafe/.codex if needed"],
        "forbidden_write_paths": ["/workspace/safe_skill", "/opt/codex-bundle"],
        "symlink_policy": "record symlinks as links; do not follow links outside mounted roots",
        "max_file_size_policy": "hash and metadata for large files; cap content capture to a configured byte limit",
        "note": "Plan only. No filesystem snapshot is executed in this stage.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate filesystem diff plan")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_filesystem_diff_plan(out_dir)
    out = out_dir / "filesystem_diff_plan.json"
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
