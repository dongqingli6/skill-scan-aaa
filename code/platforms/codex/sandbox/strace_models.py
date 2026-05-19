"""Data models for Codex safe_skill strace harness plan-only mode."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

DEFAULT_SYSCALL_FOCUS = [
    "execve",
    "openat",
    "connect",
    "socket",
    "sendto",
    "recvfrom",
    "unlink",
    "rename",
    "chmod",
    "chown",
    "mkdir",
    "rmdir",
    "clone",
]


@dataclass
class StraceHarnessConfig:
    enabled: bool = False
    plan_only: bool = True
    safe_skill_only: bool = True
    allow_strace_execution: bool = False
    allow_docker_run: bool = False
    allow_codex_exec: bool = False
    network_enabled: bool = False
    timeout_seconds: int = 60
    strace_log_path: str = "strace.log"
    syscall_focus: List[str] = field(default_factory=lambda: list(DEFAULT_SYSCALL_FOCUS))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StraceHarnessPlan:
    plan_only: bool
    strace_available_on_host: bool
    strace_path: str | None
    strace_execution_allowed: bool
    docker_run_allowed: bool
    codex_exec_allowed: bool
    safe_skill_only: bool
    network_mode: str
    command_preview: str
    syscall_focus: List[str]
    output_paths: Dict[str, str]
    safety_errors: List[str] = field(default_factory=list)
    safety_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
