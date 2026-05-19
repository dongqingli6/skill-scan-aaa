"""Docker safe smoke plan builder.

This module only writes Docker plan JSON. It never builds images, starts
containers, downloads software, or executes Codex.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:
    from core.safety_guard import assert_safe_skill_path
    from platforms.codex.sandbox.docker_preflight import validate_docker_smoke_plan
    from platforms.codex.sandbox.docker_smoke_models import CodexDockerSmokeConfig, CodexDockerSmokePlan
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from core.safety_guard import assert_safe_skill_path
    from platforms.codex.sandbox.docker_preflight import validate_docker_smoke_plan
    from platforms.codex.sandbox.docker_smoke_models import CodexDockerSmokeConfig, CodexDockerSmokePlan


def build_docker_safe_smoke_plan(
    *,
    skill_path: str | Path,
    output_dir: str | Path,
    codex_bundle_host_path: str = "/opt/codex-bundle",
) -> Dict[str, Any]:
    """Build Docker safe smoke plan-only artifacts for safe_skill."""
    skill = Path(skill_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert_safe_skill_path(skill)

    config = CodexDockerSmokeConfig()
    image_name = "codex-safe-smoke:plan-only"
    container_name = "codex-safe-smoke-plan"
    codex_bundle_mount = f"{codex_bundle_host_path}:{config.codex_bundle_inside_container}:ro"
    sample_mount = f"{skill}:{config.workspace_inside_container}/safe_skill:ro"
    output_mount = f"{out}:{config.output_inside_container}:rw"
    command_preview = (
        "DISABLED: docker run --network none "
        f"-e HOME={config.fake_home_inside_container} "
        f"-e CODEX_HOME={config.fake_codex_home_inside_container} "
        f"-e PATH={config.container_path} "
        f"-v {sample_mount} -v {output_mount} "
        f"-v {codex_bundle_mount} {image_name} "
        "codex exec --sandbox read-only --ask-for-approval never"
    )

    plan = CodexDockerSmokePlan(
        plan_only=config.plan_only,
        docker_build_allowed=config.allow_docker_build,
        docker_run_allowed=config.allow_docker_run,
        codex_exec_allowed=config.allow_codex_exec,
        image_name=image_name,
        container_name=container_name,
        sample_mount=sample_mount,
        output_mount=output_mount,
        codex_bundle_mount=codex_bundle_mount,
        network_mode="none",
        fake_home=config.fake_home_inside_container,
        fake_codex_home=config.fake_codex_home_inside_container,
        command_preview=command_preview,
        sample_mount_mode=config.sample_mount_mode,
        output_mount_mode=config.output_mount_mode,
        codex_bundle_mount_mode=config.codex_bundle_mount_mode,
        fake_home_inside_container=config.fake_home_inside_container,
        fake_codex_home_inside_container=config.fake_codex_home_inside_container,
        codex_bundle_inside_container=config.codex_bundle_inside_container,
        container_path=config.container_path,
    ).to_dict()

    preflight = validate_docker_smoke_plan(plan)
    plan["safety_errors"] = preflight["errors"]
    plan["safety_warnings"] = preflight["warnings"]

    plan_path = out / "docker_smoke_plan.json"
    preflight_path = out / "docker_preflight.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    preflight_path.write_text(json.dumps(preflight, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"plan_path": str(plan_path), "preflight_path": str(preflight_path), "plan": plan, "preflight": preflight}
