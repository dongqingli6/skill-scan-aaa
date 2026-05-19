"""Generate strace policy JSON for safe_skill plan-only mode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_policy() -> dict:
    return {
        "policy_type": "codex_safe_skill_strace_policy",
        "allowed_read_prefixes": ["/workspace", "/home/codexsafe", "/output", "/opt/codex-bundle"],
        "allowed_write_prefixes": ["/output", "/home/codexsafe/.codex"],
        "forbidden_read_patterns": [".ssh", ".env", "token", "credential", "/home/empty", "/root/.codex", "/root/.agents"],
        "forbidden_write_prefixes": ["/workspace/safe_skill", "/opt/codex-bundle"],
        "forbidden_exec_patterns": ["/bin/sh", "/bin/bash", "curl", "wget", "python", "node -e"],
        "forbidden_network_patterns": ["connect(", "api.openai.com", "0.0.0.0", "169.254.169.254"],
        "severity_mapping": {
            "external_connect": "HIGH",
            "credential_read": "HIGH",
            "host_private_read": "CRITICAL",
            "workspace_write": "HIGH",
            "codex_bundle_write": "CRITICAL",
            "shell_exec": "HIGH",
        },
        "note": "Plan-only policy. No strace execution in this stage.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate strace policy JSON")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "strace_policy.json"
    out.write_text(json.dumps(build_policy(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
