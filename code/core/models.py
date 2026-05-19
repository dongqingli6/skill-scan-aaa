"""Shared data models for multi-platform agent skill analysis.

The models in this module are intentionally dependency-free and JSON-friendly.
They are used by platform-specific adapters without importing either Claude
Code or Codex tooling.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


SUPPORTED_PLATFORMS = {"claude_code", "codex", "both", "unknown"}


def _normalize_platform(platform: str) -> str:
    value = (platform or "unknown").strip().lower()
    return value if value in SUPPORTED_PLATFORMS else "unknown"


def _path_to_str(path: Optional[str | Path]) -> Optional[str]:
    if path is None:
        return None
    return str(path)


def _paths_to_str(paths: Optional[List[str | Path]]) -> List[str]:
    return [str(path) for path in (paths or [])]


@dataclass
class SkillRecord:
    """Unified record for Claude Code, Codex, or unknown agent skills."""

    platform: str = "unknown"
    source: str = ""
    repo: str = ""
    skill_name: str = ""
    source_path: Optional[str] = None
    skill_md_path: Optional[str] = None
    agents_md_path: Optional[str] = None
    openai_yaml_path: Optional[str] = None
    scripts_paths: List[str] = field(default_factory=list)
    references_paths: List[str] = field(default_factory=list)
    assets_paths: List[str] = field(default_factory=list)
    classification: str = "unknown"
    static_findings: List[Dict[str, Any]] = field(default_factory=list)
    ai_audit_findings: List[Dict[str, Any]] = field(default_factory=list)
    dynamic_findings: List[Dict[str, Any]] = field(default_factory=list)
    severity: str = "UNKNOWN"
    confidence: float = 0.0

    def __post_init__(self) -> None:
        self.platform = _normalize_platform(self.platform)
        self.source_path = _path_to_str(self.source_path)
        self.skill_md_path = _path_to_str(self.skill_md_path)
        self.agents_md_path = _path_to_str(self.agents_md_path)
        self.openai_yaml_path = _path_to_str(self.openai_yaml_path)
        self.scripts_paths = _paths_to_str(self.scripts_paths)
        self.references_paths = _paths_to_str(self.references_paths)
        self.assets_paths = _paths_to_str(self.assets_paths)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-compatible representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillRecord":
        """Build a record from a JSON-compatible dictionary."""
        return cls(**{key: data.get(key) for key in cls.__dataclass_fields__})


def record_from_paths(
    *,
    platform: str,
    skill_dir: str | Path,
    skill_md_path: str | Path,
    source: str = "",
    repo: str = "",
    skill_name: Optional[str] = None,
    agents_md_path: Optional[str | Path] = None,
    openai_yaml_path: Optional[str | Path] = None,
    scripts_paths: Optional[List[str | Path]] = None,
    references_paths: Optional[List[str | Path]] = None,
    assets_paths: Optional[List[str | Path]] = None,
) -> SkillRecord:
    """Convenience constructor used by filesystem locators."""
    skill_dir_path = Path(skill_dir)
    return SkillRecord(
        platform=platform,
        source=source,
        repo=repo,
        skill_name=skill_name or skill_dir_path.name,
        source_path=str(skill_dir_path),
        skill_md_path=str(skill_md_path),
        agents_md_path=_path_to_str(agents_md_path),
        openai_yaml_path=_path_to_str(openai_yaml_path),
        scripts_paths=_paths_to_str(scripts_paths),
        references_paths=_paths_to_str(references_paths),
        assets_paths=_paths_to_str(assets_paths),
    )
