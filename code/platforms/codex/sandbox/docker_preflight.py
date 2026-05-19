"""Preflight validation for Docker safe smoke plan-only mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


FORBIDDEN_PREVIEW = ["--privileged", "--network host", "--yolo", "danger-full-access", "dangerously"]


def _host_path_from_mount(mount: str) -> Path:
    # The generated mount format uses absolute host paths without colons.
    host = mount.split(":", 1)[0]
    return Path(host).expanduser().resolve()


def validate_docker_smoke_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if plan.get("plan_only") is not True:
        errors.append("plan_only must be true")
    if plan.get("docker_build_allowed") is not False:
        errors.append("docker_build_allowed must be false")
    if plan.get("docker_run_allowed") is not False:
        errors.append("docker_run_allowed must be false")
    if plan.get("codex_exec_allowed") is not False:
        errors.append("codex_exec_allowed must be false")
    if plan.get("network_mode") != "none":
        errors.append("network_mode must be none")
    if plan.get("sample_mount_mode") != "read-only":
        errors.append("sample_mount_mode must be read-only")
    if plan.get("output_mount_mode") != "writable":
        errors.append("output_mount_mode must be writable")
    if plan.get("codex_bundle_mount_mode") != "read-only":
        errors.append("codex_bundle_mount_mode must be read-only")

    sample_mount_text = str(plan.get("sample_mount", ""))
    output_mount_text = str(plan.get("output_mount", ""))
    bundle_mount_text = str(plan.get("codex_bundle_mount", ""))
    if not sample_mount_text.endswith(":ro"):
        errors.append("sample_mount must end with :ro")
    if not output_mount_text.endswith(":rw"):
        errors.append("output_mount must end with :rw")
    if not bundle_mount_text.endswith(":ro"):
        errors.append("codex_bundle_mount must end with :ro")
    if ":/opt/codex-bundle:ro" not in bundle_mount_text:
        errors.append("codex_bundle_mount must target /opt/codex-bundle read-only")

    sample_mount = _host_path_from_mount(sample_mount_text)
    output_mount = _host_path_from_mount(output_mount_text)
    if output_mount == sample_mount or sample_mount in output_mount.parents:
        errors.append("output_mount must not be inside sample_mount")

    host_home = Path.home().resolve()
    fake_home = Path(str(plan.get("fake_home", "/"))).expanduser()
    fake_codex_home = Path(str(plan.get("fake_codex_home", "/"))).expanduser()
    if fake_home == host_home:
        errors.append("fake_home must not be host HOME")
    if fake_codex_home == host_home / ".codex":
        errors.append("fake_codex_home must not be host ~/.codex")

    if plan.get("container_path") != "/opt/codex-bundle/bin:/usr/local/bin:/usr/bin:/bin":
        errors.append("container_path must be restricted to the Codex bundle and system bin directories")

    preview = str(plan.get("command_preview", ""))
    for token in FORBIDDEN_PREVIEW:
        if token in preview:
            errors.append(f"forbidden command_preview token: {token}")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
