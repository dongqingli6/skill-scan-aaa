"""Safety guardrails for static-only agent skill scanning."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Mapping, Sequence


SENSITIVE_ENV_NAMES = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "CODEX_HOME",
    "SSH_AUTH_SOCK",
}

FORBIDDEN_COMMAND_PATTERNS = [
    r"\bcodex\s+exec\b",
    r"\bclaude\s+-p\b",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bnpm\s+install\b",
    r"\bpip\s+install\b",
    r"\bbash\s+-c\b",
    r"curl\s+.*\|\s*bash",
    r"\bdocker\s+run\b",
    r"run_pipeline\.sh",
    r"03_download\.sh",
    r"08_execute\.sh",
    r"run_skill\.sh",
]


def assert_static_only(mode: str) -> None:
    """Allow only static-only or dry-run static audit modes."""
    if mode not in {"static-only", "ai-audit-static"}:
        raise ValueError("Only static-only and ai-audit-static dry-run modes are allowed.")


def assert_no_real_home(path: str | os.PathLike[str]) -> None:
    """Reject paths that point exactly at the current real HOME.

    Repository checkouts commonly live under a user's home directory. Static
    scans may target an explicit repository path, but must not target HOME
    itself as a broad scan root.
    """
    candidate = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    if candidate == home:
        raise ValueError(f"Refusing to scan real HOME-derived path: {candidate}")


def assert_no_real_codex_home(path: str | os.PathLike[str]) -> None:
    """Reject paths that point at the current user's real Codex state."""
    candidate = Path(path).expanduser().resolve()
    codex_home = (Path.home() / ".codex").resolve()
    agents_home = (Path.home() / ".agents").resolve()
    for forbidden in (codex_home, agents_home):
        if candidate == forbidden or forbidden in candidate.parents:
            raise ValueError(f"Refusing to scan real Codex/Agents home path: {candidate}")


def assert_no_token_env() -> None:
    """Fail closed when sensitive environment variables are present."""
    present = sorted(name for name in SENSITIVE_ENV_NAMES if os.environ.get(name))
    if present:
        joined = ", ".join(present)
        raise ValueError(f"Sensitive environment variables are set; refusing to continue: {joined}")


def deny_dynamic_execution_unless_explicit(mode: str, allow_dynamic_execution: bool) -> None:
    """Deny dynamic mode unless a future explicit safety gate is provided."""
    if mode == "dynamic" and not allow_dynamic_execution:
        raise ValueError("Dynamic execution is disabled. Use the future Docker fake HOME sandbox only.")


def check_forbidden_command(command_string: str) -> None:
    """Reject known dangerous command strings."""
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if re.search(pattern, command_string, re.IGNORECASE):
            raise ValueError(f"Forbidden command pattern detected: {pattern}")


def check_command_list(commands: Iterable[str]) -> None:
    for command in commands:
        check_forbidden_command(command)


def assert_safe_skill_path(skill_path: str | os.PathLike[str]) -> None:
    candidate = Path(skill_path).resolve()
    expected_suffix = Path("code/platforms/codex/examples/safe_skill")
    if tuple(candidate.parts[-len(expected_suffix.parts):]) != expected_suffix.parts:
        raise ValueError(f"Smoke test is restricted to safe_skill only: {candidate}")


def assert_manual_smoke_env() -> None:
    if os.environ.get("ALLOW_CODEX_SAFE_SMOKE_TEST") != "1":
        raise ValueError("ALLOW_CODEX_SAFE_SMOKE_TEST=1 is required for any Codex smoke execution.")


def assert_minimal_env_only(env: Mapping[str, str]) -> None:
    allowed = {"HOME", "CODEX_HOME", "PATH", "LANG", "LC_ALL"}
    extra = sorted(set(env) - allowed)
    if extra:
        raise ValueError(f"Smoke test environment contains non-minimal variables: {', '.join(extra)}")


def assert_forbidden_flags_absent(command: Sequence[str] | str) -> None:
    text = " ".join(command) if not isinstance(command, str) else command
    forbidden = ["--yolo", "danger-full-access", "dangerously", "network enabled"]
    for token in forbidden:
        if token.lower() in text.lower():
            raise ValueError(f"Forbidden Codex smoke flag or phrase detected: {token}")
    check_forbidden_command(text.replace("codex exec", "codex-preview"))


def assert_no_network_requested(command_or_config: object) -> None:
    text = str(command_or_config).lower()
    if "network enabled" in text or "--network" in text or "allow_network=True".lower() in text:
        raise ValueError("Network must not be requested for safe smoke tests.")
