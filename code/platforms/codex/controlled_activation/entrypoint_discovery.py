from __future__ import annotations

import re
from pathlib import Path
from typing import Any


SAFE_WORDS = ("help", "--help", "version", "--version", "dry-run", "--dry-run", "metadata", "inspect", "list")


def discover_candidate_entrypoints(extracted_skill_dir: str | Path) -> dict[str, Any]:
    root = Path(extracted_skill_dir).resolve()
    file_tree = _file_tree(root)
    skill_md = _find_skill_md(root)
    text = ""
    if skill_md is not None:
        text = skill_md.read_text(encoding="utf-8", errors="replace")[:20000]
    candidates = _discover_from_text(text)
    if skill_md is not None:
        candidates.extend(
            [
                {"command": "metadata", "source": "generic_metadata_only", "evidence": "SKILL.md present"},
                {"command": "inspect", "source": "generic_metadata_only", "evidence": "SKILL.md present"},
            ]
        )
    return {
        "skill_md_path": str(skill_md) if skill_md else None,
        "file_tree": file_tree,
        "candidate_entrypoints": _dedupe_candidates(candidates),
    }


def _discover_from_text(text: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    lowered = text.lower()
    for word in SAFE_WORDS:
        pattern = re.escape(word.lower())
        if re.search(rf"(^|[^a-z0-9_-]){pattern}([^a-z0-9_-]|$)", lowered):
            candidates.append({"command": word, "source": "skill_documentation", "evidence": f"mentioned `{word}` in SKILL.md"})
    return candidates


def _file_tree(root: Path) -> list[str]:
    if not root.exists():
        return []
    return [
        str(path.relative_to(root))
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ][:200]


def _find_skill_md(root: Path) -> Path | None:
    for path in sorted(root.rglob("SKILL.md")):
        if path.is_file() and not path.is_symlink():
            return path
    return None


def _dedupe_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    deduped = []
    for candidate in candidates:
        command = candidate["command"]
        if command in seen:
            continue
        seen.add(command)
        deduped.append(candidate)
    return deduped
