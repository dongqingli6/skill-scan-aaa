"""Data models for Docker safe smoke plan-only mode."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class CodexDockerSmokeConfig:
    enabled: bool = False
    plan_only: bool = True
    allow_docker_build: bool = False
    allow_docker_run: bool = False
    allow_codex_exec: bool = False
    safe_skill_only: bool = True
    network_enabled: bool = False
    sample_mount_mode: str = "read-only"
    output_mount_mode: str = "writable"
    fake_home_inside_container: str = "/home/codexsafe"
    fake_codex_home_inside_container: str = "/home/codexsafe/.codex"
    workspace_inside_container: str = "/workspace"
    output_inside_container: str = "/output"
    codex_bundle_inside_container: str = "/opt/codex-bundle"
    container_path: str = "/opt/codex-bundle/bin:/usr/local/bin:/usr/bin:/bin"
    timeout_seconds: int = 60
    codex_bundle_mount_mode: str = "read-only"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodexDockerSmokePlan:
    plan_only: bool
    docker_build_allowed: bool
    docker_run_allowed: bool
    codex_exec_allowed: bool
    image_name: str
    container_name: str
    sample_mount: str
    output_mount: str
    codex_bundle_mount: str
    network_mode: str
    fake_home: str
    fake_codex_home: str
    command_preview: str
    safety_errors: List[str] = field(default_factory=list)
    safety_warnings: List[str] = field(default_factory=list)
    sample_mount_mode: str = "read-only"
    output_mount_mode: str = "writable"
    codex_bundle_mount_mode: str = "read-only"
    fake_home_inside_container: str = "/home/codexsafe"
    fake_codex_home_inside_container: str = "/home/codexsafe/.codex"
    codex_bundle_inside_container: str = "/opt/codex-bundle"
    container_path: str = "/opt/codex-bundle/bin:/usr/local/bin:/usr/bin:/bin"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
