"""Codex executor adapter draft.

This module builds safe execution plans only. It never launches Codex, Docker,
or sample scripts. Any future execution must happen in Docker and must pass
allow_dynamic_execution=True explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULT_FAKE_HOME = Path("/tmp/codex_fake_home")


def build_fake_home_layout(fake_home: str | Path = DEFAULT_FAKE_HOME) -> Dict[str, str]:
    """Return the fake Codex home layout that a sandbox should create."""
    home = Path(fake_home)
    return {
        "HOME": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "user_skills": str(home / ".agents" / "skills"),
        "codex_config": str(home / ".codex" / "config.toml"),
        "fake_credentials": str(home / "fake_credentials"),
    }


def validate_no_real_home(paths: Iterable[str | Path]) -> None:
    """Reject plans that reference the current real HOME."""
    real_home = Path(os.path.expanduser("~")).resolve()
    for value in paths:
        path = Path(value).expanduser()
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path.absolute()
        if resolved == real_home or real_home in resolved.parents:
            raise ValueError(f"Refusing to use real HOME path: {resolved}")


def validate_no_real_tokens(env: Dict[str, str]) -> None:
    """Reject plans that attempt to pass real token-like environment values."""
    sensitive_names = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "SSH_AUTH_SOCK",
        "CODEX_AUTH_TOKEN",
    }
    for key in sensitive_names:
        value = env.get(key)
        if value and not value.startswith("FAKE_"):
            raise ValueError(f"Refusing to pass real-looking token variable: {key}")


def build_codex_execution_plan(
    *,
    sample_path: str | Path,
    output_dir: str | Path,
    fake_home: str | Path = DEFAULT_FAKE_HOME,
    allow_dynamic_execution: bool = False,
) -> Dict[str, Any]:
    """Build a non-executing Codex sandbox plan."""
    layout = build_fake_home_layout(fake_home)
    validate_no_real_home([layout["HOME"], layout["CODEX_HOME"], sample_path, output_dir])

    env = {
        "HOME": layout["HOME"],
        "CODEX_HOME": layout["CODEX_HOME"],
        "OPENAI_API_KEY": "FAKE_OPENAI_API_KEY_FOR_HONEYPOT_ONLY",
        "GITHUB_TOKEN": "FAKE_GITHUB_TOKEN_FOR_HONEYPOT_ONLY",
    }
    validate_no_real_tokens(env)

    return {
        "platform": "codex",
        "dynamic_execution_allowed": bool(allow_dynamic_execution),
        "will_execute": False,
        "requires_docker": True,
        "network": False,
        "sandbox_mode": "read-only",
        "approval_policy": "never",
        "allow_yolo": False,
        "mounts": {
            "sample": {"source": str(sample_path), "target": "/workspace/sample", "mode": "ro"},
            "output": {"source": str(output_dir), "target": "/analysis/output", "mode": "rw"},
        },
        "env": env,
        "logs": {
            "codex_output": "codex_output.txt",
            "strace": "strace.log",
            "network": "network.pcap",
            "filesystem_changes": "filesystem_changes.json",
            "activation_trace": "skill_activation_trace.json",
        },
        "future_command_template": [
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "--json",
        ],
        "safety_note": "This is a plan only. No command is executed by this adapter.",
    }
