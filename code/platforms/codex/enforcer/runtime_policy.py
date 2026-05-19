"""Policy-as-code loader and validator for Codex runtime enforcement."""

from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_POLICY = Path(__file__).resolve().with_name("policy.yaml")


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    severity: str
    matched_rule: str
    recommended_action: str


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def load_policy(path: str | Path = DEFAULT_POLICY) -> dict[str, Any]:
    """Load the repository policy YAML subset without external dependencies."""
    policy_path = Path(path)
    data: dict[str, Any] = {}
    current_key: str | None = None
    current_map: dict[str, Any] | None = None
    current_list: list[Any] | None = None

    for raw in policy_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            key, _, value = line.partition(":")
            current_key = key.strip()
            value = value.strip()
            if value:
                data[current_key] = _parse_scalar(value)
                current_map = None
                current_list = None
            else:
                data[current_key] = []
                current_map = None
                current_list = data[current_key]
            continue
        if current_key is None:
            raise ValueError(f"invalid policy line before key: {line}")
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_list is None:
                data[current_key] = []
                current_list = data[current_key]
                current_map = None
            current_list.append(_parse_scalar(stripped[2:]))
            continue
        key, _, value = stripped.partition(":")
        if not value:
            raise ValueError(f"nested policy maps are not supported: {line}")
        if current_map is None:
            data[current_key] = {}
            current_map = data[current_key]
            current_list = None
        current_map[key.strip()] = _parse_scalar(value.strip())

    return data


def resolve_repo_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    return candidate.resolve()


def _response_for(policy: dict[str, Any], severity: str) -> str:
    runtime = policy.get("runtime_response", {})
    return runtime.get(f"on_{severity.lower()}_violation", "fail_closed")


def _deny(policy: dict[str, Any], reason: str, severity: str, matched_rule: str) -> PolicyDecision:
    return PolicyDecision(
        allowed=False,
        reason=reason,
        severity=severity,
        matched_rule=matched_rule,
        recommended_action=_response_for(policy, severity),
    )


def validate_skill_path(policy: dict[str, Any], skill_path: str | Path) -> PolicyDecision:
    resolved = resolve_repo_path(skill_path)
    name_parts = set(resolved.parts)
    for forbidden in policy.get("forbidden_skill_names", []):
        if forbidden in name_parts or forbidden in str(resolved):
            return _deny(policy, f"forbidden skill matched: {forbidden}", "CRITICAL", "forbidden_skill_names")

    allowed = [resolve_repo_path(path) for path in policy.get("allowed_skill_roots", [])]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        return _deny(policy, f"skill path is outside allowed roots: {resolved}", "HIGH", "allowed_skill_roots")

    return PolicyDecision(
        allowed=True,
        reason=f"skill path is allowed: {resolved}",
        severity="LOW",
        matched_rule="allowed_skill_roots",
        recommended_action="allow_plan_or_enforce",
    )


def validate_path(policy: dict[str, Any], path: str | Path) -> PolicyDecision:
    text = str(path)
    for allowed in policy.get("allowed_fake_paths", []):
        if text.startswith(allowed):
            return PolicyDecision(True, f"fake path allowed: {text}", "LOW", "allowed_fake_paths", "allow")
    for forbidden in policy.get("forbidden_paths", []):
        expanded = str(Path(forbidden).expanduser()) if forbidden.startswith("~") else forbidden
        if forbidden in text or expanded in text:
            return _deny(policy, f"forbidden path matched: {forbidden}", "CRITICAL", "forbidden_paths")
    return PolicyDecision(True, f"path allowed by default path checks: {text}", "LOW", "path_policy", "allow")


def validate_command(policy: dict[str, Any], command: str | list[str]) -> PolicyDecision:
    if isinstance(command, str):
        parts = shlex.split(command)
        command_text = command
    else:
        parts = [str(part) for part in command]
        command_text = " ".join(parts)
    forbidden_commands = policy.get("forbidden_commands", [])
    for forbidden in forbidden_commands:
        if " " in forbidden:
            if forbidden in command_text:
                return _deny(policy, f"forbidden command sequence matched: {forbidden}", "HIGH", "forbidden_commands")
        elif any(Path(part).name == forbidden for part in parts):
            return _deny(policy, f"forbidden command matched: {forbidden}", "HIGH", "forbidden_commands")
    return PolicyDecision(True, "command allowed by policy", "LOW", "forbidden_commands", "allow")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Codex runtime policy inputs")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--skill-path")
    parser.add_argument("--path")
    parser.add_argument("--command")
    args = parser.parse_args()

    policy = load_policy(args.policy)
    if args.skill_path:
        decision = validate_skill_path(policy, args.skill_path)
    elif args.path:
        decision = validate_path(policy, args.path)
    elif args.command:
        decision = validate_command(policy, args.command)
    else:
        decision = PolicyDecision(True, "policy loaded", "LOW", "policy", "allow")
    print(json.dumps(asdict(decision), indent=2, ensure_ascii=False))
    return 0 if decision.allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
