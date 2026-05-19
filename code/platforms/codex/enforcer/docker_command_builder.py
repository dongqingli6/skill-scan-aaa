"""Build Docker sandbox command previews for Codex runtime enforcement."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.enforcer.egress.egress_policy import load_egress_policy, summarize_egress_policy
    from platforms.codex.enforcer.runtime_policy import load_policy, resolve_repo_path, validate_skill_path
else:  # pragma: no cover
    from .egress.egress_policy import load_egress_policy, summarize_egress_policy
    from .runtime_policy import load_policy, resolve_repo_path, validate_skill_path


DEFAULT_IMAGE = "codex-safe-smoke:strace"
CONTAINER_NAME = "codex-runtime-enforced-plan"
FAKE_HOME_INIT_SCRIPT = (
    "mkdir -p /home/codexsafe/.codex; "
    "mkdir -p /home/codexsafe/.agents; "
    "mkdir -p /output; "
    "chmod 700 /home/codexsafe /home/codexsafe/.codex /home/codexsafe/.agents; "
)


def build_docker_command_preview(
    *,
    policy: dict[str, Any],
    skill_path: str | Path,
    output_dir: str | Path,
    codex_bundle_ro: str | Path,
    image: str = DEFAULT_IMAGE,
    seccomp_profile: str | Path | None = None,
    apparmor_profile: str | None = None,
    egress_policy: str | Path | None = None,
    network_mode: str = "none",
) -> dict[str, Any]:
    decision = validate_skill_path(policy, skill_path)
    sample = resolve_repo_path(skill_path)
    output = resolve_repo_path(output_dir)
    bundle = resolve_repo_path(codex_bundle_ro)
    docker_policy = policy.get("docker_policy", {})
    preview_network_mode = "none" if network_mode not in {"none", "controlled"} else network_mode
    docker_network_mode = "none"
    egress_summary = summarize_egress_policy(load_egress_policy(egress_policy))

    hardening_options: list[str] = []
    if seccomp_profile:
        hardening_options.extend(["--security-opt", f"seccomp={seccomp_profile}"])
    if apparmor_profile:
        hardening_options.extend(["--security-opt", f"apparmor={apparmor_profile}"])

    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        CONTAINER_NAME,
        "--network",
        docker_network_mode,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        *hardening_options,
        "--pids-limit",
        str(docker_policy.get("pids_limit", 256)),
        "--memory",
        str(docker_policy.get("memory_limit", "1g")),
        "--cpus",
        str(docker_policy.get("cpus", "1.0")),
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--tmpfs",
        "/home/codexsafe:rw,nosuid,nodev,uid=1000,gid=1000,mode=700",
        "-e",
        "HOME=/home/codexsafe",
        "-e",
        "CODEX_HOME=/home/codexsafe/.codex",
        "-e",
        "PATH=/opt/codex-bundle/bin:/usr/local/bin:/usr/bin:/bin",
        "-v",
        f"{sample}:/workspace/safe_skill:ro",
        "-v",
        f"{output}:/output:rw",
        "-v",
        f"{bundle}:/opt/codex-bundle:ro",
        image,
        "/bin/bash",
        "-lc",
        FAKE_HOME_INIT_SCRIPT + "echo enforce mode is not enabled in plan-only preview",
    ]

    forbidden_fragments = [
        "--privileged",
        "--network host",
        "/var/run/docker.sock",
        str(Path.home() / ".codex"),
        str(Path.home() / ".agents"),
        f"{Path.home()}:/",
        ".env:/",
    ]
    preview = " ".join(shlex.quote(part) for part in command)
    safety_errors = [fragment for fragment in forbidden_fragments if fragment and fragment in preview]

    return {
        "policy_decision": decision.__dict__,
        "command": command,
        "command_preview": preview,
        "expected_mounts": {
            "sample": f"{sample}:/workspace/safe_skill:ro",
            "output": f"{output}:/output:rw",
            "codex_bundle": f"{bundle}:/opt/codex-bundle:ro",
        },
        "sandbox_hardening": {
            "plan_only": True,
            "seccomp_profile": str(seccomp_profile) if seccomp_profile else None,
            "apparmor_profile": apparmor_profile,
            "production_enabled": False,
            "note": "Prototype hardening options are previewed only; enforce-mode activation requires manual review and safe_skill-only testing.",
        },
        "expected_network_policy": {
            "network_mode": preview_network_mode,
            "docker_network_mode": docker_network_mode,
            "network_default": policy.get("network_policy", {}).get("default", "deny"),
            "allow_openai_api": policy.get("network_policy", {}).get("allow_openai_api", False),
            "allow_dns": policy.get("network_policy", {}).get("allow_dns", False),
            "egress_policy_path": str(egress_policy) if egress_policy else None,
            "egress_policy": egress_summary["egress_policy"],
            "egress_proxy_enabled": False,
            "controlled_network_preview_only": preview_network_mode == "controlled",
        },
        "expected_enforcement_response": policy.get("runtime_response", {}),
        "safety_errors": safety_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Docker command preview for Codex enforcement")
    parser.add_argument("--policy", required=True)
    parser.add_argument("--skill-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--codex-bundle-ro", required=True)
    parser.add_argument("--seccomp-profile")
    parser.add_argument("--apparmor-profile")
    parser.add_argument("--egress-policy")
    parser.add_argument("--network-mode", choices=["none", "controlled"], default="none")
    parser.add_argument("--output")
    args = parser.parse_args()

    policy = load_policy(args.policy)
    result = build_docker_command_preview(
        policy=policy,
        skill_path=args.skill_path,
        output_dir=args.output_dir,
        codex_bundle_ro=args.codex_bundle_ro,
        seccomp_profile=args.seccomp_profile,
        apparmor_profile=args.apparmor_profile,
        egress_policy=args.egress_policy,
        network_mode=args.network_mode,
    )
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["policy_decision"].get("allowed") and not result["safety_errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
