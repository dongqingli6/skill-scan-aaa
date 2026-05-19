"""Fail-closed Codex safe_skill smoke test runner."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

try:
    from core.safety_guard import (
        assert_manual_smoke_env,
        assert_minimal_env_only,
        assert_no_real_codex_home,
        assert_no_real_home,
        assert_no_token_env,
        assert_safe_skill_path,
    )
    from platforms.codex.sandbox.codex_command import build_codex_safe_smoke_command
    from platforms.codex.sandbox.fake_home import build_fake_home_layout
    from platforms.codex.sandbox.smoke_models import CodexSmokeTestConfig, CodexSmokeTestResult
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from core.safety_guard import (
        assert_manual_smoke_env,
        assert_minimal_env_only,
        assert_no_real_codex_home,
        assert_no_real_home,
        assert_no_token_env,
        assert_safe_skill_path,
    )
    from platforms.codex.sandbox.codex_command import build_codex_safe_smoke_command
    from platforms.codex.sandbox.fake_home import build_fake_home_layout
    from platforms.codex.sandbox.smoke_models import CodexSmokeTestConfig, CodexSmokeTestResult


def prepare_codex_safe_smoke_test(
    *,
    skill_path: str | Path,
    output_dir: str | Path,
    enabled: bool = False,
    allow_codex_exec: bool = False,
    safe_skill_only: bool = True,
) -> Dict[str, Any]:
    """Prepare fake HOME and smoke test config for safe_skill only."""
    skill = Path(skill_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert_safe_skill_path(skill)
    layout = build_fake_home_layout(out, skill, "safe_skill")
    config = CodexSmokeTestConfig(
        enabled=enabled,
        allow_codex_exec=allow_codex_exec,
        safe_skill_only=safe_skill_only,
        skill_name="safe_skill",
        skill_path=str(skill),
        fake_home=layout["fake_home"],
        fake_codex_home=layout["fake_codex_home"],
        output_dir=str(out),
    )
    command = build_codex_safe_smoke_command(config)
    plan = {**config.to_dict(), **command}
    (out / "smoke_test_plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"config": config, "plan": plan}


def _validate_execution_allowed(config: CodexSmokeTestConfig) -> tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    checks = [
        (config.enabled, "config.enabled must be true"),
        (config.allow_codex_exec, "config.allow_codex_exec must be true"),
        (config.safe_skill_only, "safe_skill_only must be true"),
        (not config.network_enabled, "network_enabled must be false"),
        (config.approval_policy == "never", "approval_policy must be never"),
        (config.sandbox_mode in {"read-only", "workspace-write"}, "sandbox_mode must be read-only or workspace-write"),
    ]
    for ok, message in checks:
        if not ok:
            errors.append(message)

    for check in (
        lambda: assert_safe_skill_path(config.skill_path),
        lambda: assert_no_real_home(config.fake_home),
        lambda: assert_no_real_codex_home(config.fake_codex_home),
        assert_no_token_env,
        assert_manual_smoke_env,
    ):
        try:
            check()
        except ValueError as exc:
            errors.append(str(exc))
    return errors, warnings


def run_codex_safe_smoke_test(config: CodexSmokeTestConfig) -> Dict[str, Any]:
    """Run only when all explicit gates are open; otherwise fail closed."""
    output = Path(config.output_dir)
    stdout_path = output / "codex_smoke_stdout.txt"
    stderr_path = output / "codex_smoke_stderr.txt"
    command_info = build_codex_safe_smoke_command(config)
    errors, warnings = _validate_execution_allowed(config)

    if errors:
        result = CodexSmokeTestResult(
            attempted=True,
            performed=False,
            success=False,
            exit_code=None,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            command_preview=str(command_info["command_preview"]),
            safety_errors=errors,
            safety_warnings=warnings,
            notes=["Codex was not executed; fail-closed safety gate blocked execution."],
        )
        return result.to_dict()

    env = {
        "HOME": config.fake_home,
        "CODEX_HOME": config.fake_codex_home,
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    assert_minimal_env_only(env)
    cwd = Path(config.fake_home) / "workspace"
    cwd.mkdir(parents=True, exist_ok=True)

    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(
            command_info["command"],
            cwd=str(cwd),
            env=env,
            stdout=stdout,
            stderr=stderr,
            text=True,
            timeout=config.timeout_seconds,
            check=False,
        )

    result = CodexSmokeTestResult(
        attempted=True,
        performed=True,
        success=completed.returncode == 0,
        exit_code=completed.returncode,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        command_preview=str(command_info["command_preview"]),
        safety_errors=[],
        safety_warnings=warnings,
        notes=["Codex safe_skill smoke test executed under explicit manual gates."],
    )
    return result.to_dict()
