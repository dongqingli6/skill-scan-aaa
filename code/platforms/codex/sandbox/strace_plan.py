"""Write a plan for future strace collection. Does not execute strace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_strace_plan(output_dir: str | Path) -> dict:
    return {
        "plan_type": "strace_plan",
        "execution_enabled": False,
        "trace_file": "strace.log",
        "syscalls_of_interest": [
            "openat",
            "connect",
            "execve",
            "unlink",
            "rename",
            "chmod",
            "chown",
            "mkdir",
            "socket",
            "sendto",
            "recvfrom",
        ],
        "suspicious_syscall_patterns": [
            "credential file read",
            "network connect",
            "shell execution",
            "writes outside output",
        ],
        "note": "Plan only. strace is not executed in this stage.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate strace plan")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_strace_plan(out_dir)
    out = out_dir / "strace_plan.json"
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
