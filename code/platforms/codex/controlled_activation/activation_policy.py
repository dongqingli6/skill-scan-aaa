from __future__ import annotations

from typing import Any


ALLOWED_SAMPLE_NAMES = ("ideation.zip", "react-effect-patterns.zip")
FORBIDDEN_SAMPLE_NAMES = ("implementation-guide.zip", "logging-best-practices.zip", "val-town-cli.zip")
ALLOWED_ACTIVATION_COMMANDS = ("help", "--help", "version", "--version", "dry-run", "--dry-run", "metadata", "inspect", "list")
FORBIDDEN_PATTERNS = (
    "curl",
    "wget",
    "npm install",
    "pip install",
    "apt install",
    "bash",
    "sh",
    "python -c",
    "node -e",
    "eval",
    "exec",
    "sudo",
    "docker",
    "ssh",
    "scp",
    "nc",
    "netcat",
    "/var/run/docker.sock",
    "~/.codex",
    "~/.agents",
    ".env",
    "id_rsa",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
)


def evaluate_activation_policy(
    sample_name: str,
    deterministic_risk: dict[str, int],
    agent_aggregate_risk: dict[str, int],
    candidate_entrypoints: list[dict[str, Any]],
    *,
    stage21_passed: bool,
    stage23_passed: bool,
    human_confirmed: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    denied_entrypoints: list[dict[str, Any]] = []
    allowed_entrypoints: list[dict[str, Any]] = []

    if sample_name not in ALLOWED_SAMPLE_NAMES:
        blockers.append("sample is not in controlled activation allowlist")
    if sample_name in FORBIDDEN_SAMPLE_NAMES:
        blockers.append("sample is explicitly forbidden for controlled activation")
    if _has_any_risk(deterministic_risk, ("critical", "high", "medium")):
        blockers.append("deterministic C/H/M risk blocks controlled activation")
    if _has_any_risk(agent_aggregate_risk, ("critical", "high")):
        blockers.append("agent aggregate HIGH / CRITICAL risk blocks controlled activation")
    if not stage21_passed:
        blockers.append("Stage 21 controlled benign inspection has not passed")
    if not stage23_passed:
        blockers.append("Stage 23 repeatability monitoring has not passed")

    for entrypoint in candidate_entrypoints:
        command = str(entrypoint.get("command", ""))
        decision = evaluate_entrypoint_command(command)
        enriched = {**entrypoint, **decision}
        if decision["allowed"]:
            allowed_entrypoints.append(enriched)
        else:
            denied_entrypoints.append(enriched)

    if candidate_entrypoints and denied_entrypoints and not allowed_entrypoints:
        blockers.append("unsafe entrypoint denied")

    if not candidate_entrypoints or (not allowed_entrypoints and not blockers):
        if not blockers:
            return {
                "decision": "skip",
                "reason": "no safe entrypoint discovered",
                "blockers": [],
                "allowed_entrypoints": [],
                "denied_entrypoints": denied_entrypoints,
                "requires_human_confirmation": False,
                "can_execute": False,
            }
        blockers.append("no safe entrypoint discovered")

    if blockers:
        return {
            "decision": "denied",
            "reason": "controlled activation denied by policy",
            "blockers": blockers,
            "allowed_entrypoints": allowed_entrypoints,
            "denied_entrypoints": denied_entrypoints,
            "requires_human_confirmation": False,
            "can_execute": False,
        }

    if not human_confirmed:
        return {
            "decision": "requires_human_confirmation",
            "reason": "safe low-risk entrypoint requires human confirmation",
            "blockers": [],
            "allowed_entrypoints": allowed_entrypoints,
            "denied_entrypoints": denied_entrypoints,
            "requires_human_confirmation": True,
            "can_execute": False,
        }

    return {
        "decision": "allowed",
        "reason": "human confirmed controlled activation",
        "blockers": [],
        "allowed_entrypoints": allowed_entrypoints,
        "denied_entrypoints": denied_entrypoints,
        "requires_human_confirmation": False,
        "can_execute": True,
    }


def evaluate_entrypoint_command(command: str) -> dict[str, Any]:
    normalized = " ".join(command.strip().split())
    lowered = normalized.lower()
    if normalized not in ALLOWED_ACTIVATION_COMMANDS:
        return {"allowed": False, "reason": "entrypoint is not in the safe activation command allowlist"}
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in lowered:
            return {"allowed": False, "reason": f"entrypoint contains forbidden pattern: {pattern}"}
    return {"allowed": True, "reason": "entrypoint is allowed safe activation command"}


def _has_any_risk(risk: dict[str, int], severities: tuple[str, ...]) -> bool:
    return any(int(risk.get(severity, 0) or 0) > 0 for severity in severities)
