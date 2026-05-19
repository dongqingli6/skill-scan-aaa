"""Codex sandbox run plan builder.

This module writes run plans and preflight results only. It never launches
Codex, Docker, shells, or sample code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:
    from platforms.codex.sandbox.fake_home import build_fake_home_layout
    from platforms.codex.sandbox.preflight import (
        combine_results,
        validate_dynamic_disabled_by_default,
        validate_fake_home_paths,
        validate_no_real_home_reference,
        validate_no_sensitive_env,
        validate_no_symlink_escape,
        validate_sandbox_config,
        validate_skill_path_inside_allowed_root,
    )
    from platforms.codex.sandbox.sandbox_models import CodexRunPlan, CodexSandboxConfig
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.sandbox.fake_home import build_fake_home_layout
    from platforms.codex.sandbox.preflight import (
        combine_results,
        validate_dynamic_disabled_by_default,
        validate_fake_home_paths,
        validate_no_real_home_reference,
        validate_no_sensitive_env,
        validate_no_symlink_escape,
        validate_sandbox_config,
        validate_skill_path_inside_allowed_root,
    )
    from platforms.codex.sandbox.sandbox_models import CodexRunPlan, CodexSandboxConfig


def build_codex_run_plan(
    skill_path: str | Path,
    output_dir: str | Path,
    allow_dynamic_execution: bool = False,
    allowed_root: str | Path | None = None,
) -> Dict[str, Any]:
    """Build a disabled Codex run plan and write run_plan/preflight JSON."""
    skill = Path(skill_path).resolve()
    skill_name = skill.name
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    config = CodexSandboxConfig(dynamic_execution_enabled=False)
    paths = build_fake_home_layout(out, skill, skill_name)
    preflight = combine_results(
        [
            validate_sandbox_config(config),
            validate_dynamic_disabled_by_default(config),
            validate_fake_home_paths(paths),
            validate_no_real_home_reference(paths),
            validate_no_sensitive_env(),
            validate_no_symlink_escape(skill),
            validate_skill_path_inside_allowed_root(skill, allowed_root or skill.parent),
        ]
    )

    plan = CodexRunPlan(
        platform="codex",
        skill_name=skill_name,
        skill_path=str(skill),
        fake_home=paths["fake_home"],
        fake_codex_home=paths["fake_codex_home"],
        sample_mount_mode="read-only",
        output_dir=paths["output_dir"],
        network_enabled=False,
        command_preview="DISABLED: codex exec would run here only inside Docker fake HOME sandbox",
        dynamic_execution_enabled=bool(allow_dynamic_execution and config.dynamic_execution_enabled),
        safety_status=preflight,
    ).to_dict()

    run_plan_path = out / "run_plan.json"
    preflight_path = out / "preflight.json"
    run_plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    preflight_path.write_text(json.dumps(preflight, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "run_plan_path": str(run_plan_path),
        "preflight_path": str(preflight_path),
        "run_plan": plan,
        "preflight": preflight,
    }
