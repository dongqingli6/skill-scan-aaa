"""Codex command construction for safe smoke tests.

This module only builds command lists and previews. It never executes Codex.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

try:
    from core.safety_guard import assert_forbidden_flags_absent, assert_no_network_requested, assert_safe_skill_path
    from platforms.codex.sandbox.smoke_models import CodexSmokeTestConfig
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from core.safety_guard import assert_forbidden_flags_absent, assert_no_network_requested, assert_safe_skill_path
    from platforms.codex.sandbox.smoke_models import CodexSmokeTestConfig


def build_codex_safe_smoke_command(config: CodexSmokeTestConfig) -> Dict[str, object]:
    """Build a disabled-by-default Codex smoke command for safe_skill only."""
    assert_safe_skill_path(config.skill_path)
    if config.skill_name != "safe_skill":
        raise ValueError("safe smoke command only supports skill_name=safe_skill")
    if config.network_enabled:
        raise ValueError("network must be disabled for safe smoke tests")
    if config.approval_policy != "never":
        raise ValueError("approval_policy must be never")
    if config.sandbox_mode not in {"read-only", "workspace-write"}:
        raise ValueError("sandbox_mode must be read-only or workspace-write")

    command: List[str] = [
        "codex",
        "exec",
        "--cd",
        str(Path(config.fake_home) / "workspace"),
        "--sandbox",
        config.sandbox_mode,
        "--ask-for-approval",
        config.approval_policy,
        "--skip-git-repo-check",
        "Use $safe-text-cleanup to summarize this static smoke test sentence.",
    ]
    command_preview = (
        f"HOME={config.fake_home} CODEX_HOME={config.fake_codex_home} "
        f"approval_policy={config.approval_policy} sandbox_mode={config.sandbox_mode} "
        + " ".join(command)
    )
    assert_forbidden_flags_absent(command)
    assert_no_network_requested(command_preview)
    return {"command": command, "command_preview": command_preview}
