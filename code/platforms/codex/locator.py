"""Codex Agent Skill locator.

This module performs filesystem discovery only. It does not execute scripts,
load real user-level Codex state, or read paths outside the caller-provided
scan root.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from core.models import SkillRecord, record_from_paths
except ImportError:  # pragma: no cover - supports direct module use
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from core.models import SkillRecord, record_from_paths


AGENT_GUIDANCE_FILES = ("AGENTS.override.md", "AGENTS.md")
CODEX_MANIFEST = Path("agents") / "openai.yaml"
CODEX_SKILL_ROOT = Path(".agents") / "skills"


def codex_path_models() -> List[str]:
    """Return known Codex skill path patterns without reading them."""
    return [
        ".agents/skills/<skill-name>/SKILL.md",
        "$HOME/.agents/skills/<skill-name>/SKILL.md",
        "/etc/codex/skills/<skill-name>/SKILL.md",
    ]


def _safe_rglob(root: Path, pattern: str) -> Iterable[Path]:
    try:
        yield from root.rglob(pattern)
    except (OSError, PermissionError):
        return


def _nearest_agent_guidance(skill_dir: Path, scan_root: Path) -> Optional[Path]:
    current = skill_dir
    scan_root = scan_root.resolve()
    while True:
        for filename in AGENT_GUIDANCE_FILES:
            candidate = current / filename
            if candidate.exists():
                return candidate
        if current.resolve() == scan_root or current.parent == current:
            return None
        current = current.parent


def _collect_files(directory: Path) -> List[str]:
    if not directory.exists() or not directory.is_dir():
        return []
    results: List[str] = []
    for item in _safe_rglob(directory, "*"):
        if item.is_file():
            results.append(str(item))
    return sorted(results)


def find_agents_files(root_path: str | os.PathLike[str]) -> List[str]:
    """Find AGENTS guidance files below a caller-provided root."""
    root = Path(root_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []

    results: List[str] = []
    for filename in AGENT_GUIDANCE_FILES:
        for path in _safe_rglob(root, filename):
            if path.is_file():
                results.append(str(path))
    return sorted(set(results))


def find_codex_related_files(skill_dir: str | os.PathLike[str]) -> Dict[str, object]:
    """Find Codex-related files for a skill directory without executing them."""
    directory = Path(skill_dir).expanduser().resolve()
    openai_yaml = directory / CODEX_MANIFEST
    return {
        "skill_dir": str(directory),
        "skill_md_path": str(directory / "SKILL.md") if (directory / "SKILL.md").exists() else None,
        "openai_yaml_path": str(openai_yaml) if openai_yaml.exists() else None,
        "scripts_paths": _collect_files(directory / "scripts"),
        "references_paths": _collect_files(directory / "references"),
        "assets_paths": _collect_files(directory / "assets"),
    }


def _repo_scoped_skill(skill_dir: Path) -> bool:
    parts = skill_dir.parts
    return ".agents" in parts and "skills" in parts


def build_skill_record(skill_md: Path, scan_root: Path) -> SkillRecord:
    """Build a Codex SkillRecord from a discovered SKILL.md path."""
    skill_dir = skill_md.parent
    related = find_codex_related_files(skill_dir)
    openai_yaml = Path(related["openai_yaml_path"]) if related["openai_yaml_path"] else None
    agents_md = _nearest_agent_guidance(skill_dir, scan_root)

    source = "codex_repo_skill" if _repo_scoped_skill(skill_dir) else "codex_skill"

    return record_from_paths(
        platform="codex",
        source=source,
        repo="",
        skill_name=skill_dir.name,
        skill_dir=skill_dir,
        skill_md_path=skill_md,
        agents_md_path=agents_md,
        openai_yaml_path=openai_yaml,
        scripts_paths=related["scripts_paths"],
        references_paths=related["references_paths"],
        assets_paths=related["assets_paths"],
    )


def find_codex_skills(scan_root: str | os.PathLike[str]) -> List[SkillRecord]:
    """Recursively discover Codex skills below a caller-provided directory."""
    root = Path(scan_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []

    records = []
    seen = set()
    for skill_md in _safe_rglob(root, "SKILL.md"):
        if not skill_md.is_file():
            continue
        resolved = str(skill_md.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        records.append(build_skill_record(skill_md, root))

    return records


def find_codex_skills_as_dicts(scan_root: str | os.PathLike[str]) -> List[dict]:
    """Return discovered Codex skills as JSON-compatible dictionaries."""
    return [record.to_dict() for record in find_codex_skills(scan_root)]
