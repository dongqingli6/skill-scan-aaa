"""Data models for Codex sandbox plan-only mode."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class CodexSandboxConfig:
    dynamic_execution_enabled: bool = False
    allow_codex_exec: bool = False
    allow_network: bool = False
    allow_real_home: bool = False
    allow_real_tokens: bool = False
    allow_yolo: bool = False
    sandbox_mode: str = "read-only"
    approval_policy: str = "never"
    timeout_seconds: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodexSandboxPaths:
    fake_home: str
    fake_codex_home: str
    fake_agents_dir: str
    sample_mount: str
    output_dir: str
    logs_dir: str
    config_toml_path: str
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodexRunPlan:
    platform: str
    skill_name: str
    skill_path: str
    fake_home: str
    fake_codex_home: str
    sample_mount_mode: str
    output_dir: str
    network_enabled: bool
    command_preview: str
    dynamic_execution_enabled: bool
    safety_status: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodexRunQueueItem:
    platform: str
    skill_name: str
    skill_path: str
    run_plan_path: str
    preflight_path: str
    allow_dynamic_execution: bool
    network_enabled: bool
    fake_home_required: bool
    real_home_allowed: bool
    real_tokens_allowed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
