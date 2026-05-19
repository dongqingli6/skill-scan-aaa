"""Models for Codex safe_skill smoke test harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CodexSmokeTestConfig:
    skill_name: str
    skill_path: str
    fake_home: str
    fake_codex_home: str
    output_dir: str
    enabled: bool = False
    allow_codex_exec: bool = False
    safe_skill_only: bool = True
    timeout_seconds: int = 60
    network_enabled: bool = False
    approval_policy: str = "never"
    sandbox_mode: str = "read-only"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodexSmokeTestResult:
    attempted: bool
    performed: bool
    success: bool
    exit_code: Optional[int]
    stdout_path: str
    stderr_path: str
    command_preview: str
    safety_errors: List[str] = field(default_factory=list)
    safety_warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
