"""Generate safe_skill strace harness plan-only JSON."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from platforms.codex.sandbox.strace_models import DEFAULT_SYSCALL_FOCUS, StraceHarnessConfig, StraceHarnessPlan
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.sandbox.strace_models import DEFAULT_SYSCALL_FOCUS, StraceHarnessConfig, StraceHarnessPlan

FORBIDDEN_PREVIEW = [
    "--privileged",
    "--network host",
    "--yolo",
    "danger-full-access",
    "dangerously",
    "curl",
    "wget",
    "apt install",
    "npm install",
    "pip install",
]


def build_strace_harness_plan(output_dir: str | Path) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    config = StraceHarnessConfig()
    strace_path = shutil.which("strace")
    command_preview = "DISABLED: future strace wrapper would run docker safe_skill smoke test here"
    errors = [f"forbidden preview token: {token}" for token in FORBIDDEN_PREVIEW if token in command_preview]
    plan = StraceHarnessPlan(
        plan_only=config.plan_only,
        strace_available_on_host=bool(strace_path),
        strace_path=strace_path,
        strace_execution_allowed=config.allow_strace_execution,
        docker_run_allowed=config.allow_docker_run,
        codex_exec_allowed=config.allow_codex_exec,
        safe_skill_only=config.safe_skill_only,
        network_mode="none",
        command_preview=command_preview,
        syscall_focus=list(DEFAULT_SYSCALL_FOCUS),
        output_paths={
            "strace_log": str(out / config.strace_log_path),
            "strace_parse_result": str(out / "strace_parse_result.json"),
            "strace_policy": str(out / "strace_policy.json"),
        },
        safety_errors=errors,
        safety_warnings=[] if strace_path else ["strace is not available on host"],
    ).to_dict()
    plan_path = out / "strace_harness_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate strace harness plan-only JSON")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    plan = build_strace_harness_plan(args.output_dir)
    print(Path(args.output_dir) / "strace_harness_plan.json")
    return 1 if plan.get("safety_errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
