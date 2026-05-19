"""Fake HOME layout builder for Codex sandbox plan-only mode."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

try:
    from platforms.codex.sandbox.sandbox_models import CodexSandboxPaths
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.sandbox.sandbox_models import CodexSandboxPaths


def _copy_tree_no_symlinks(src: Path, dst: Path, warnings: List[str]) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_symlink():
            warnings.append(f"Skipped symlink without following it: {item}")
            continue
        if item.is_dir():
            _copy_tree_no_symlinks(item, target, warnings)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def build_fake_home_layout(base_dir: str | Path, skill_path: str | Path, skill_name: str) -> Dict[str, Any]:
    """Create a fake HOME layout and copy a skill into fake .agents/skills."""
    base = Path(base_dir).resolve()
    skill = Path(skill_path).resolve()
    warnings: List[str] = []

    fake_home = base / "fake_home"
    fake_codex_home = fake_home / ".codex"
    fake_agents_dir = fake_home / ".agents" / "skills"
    workspace = fake_home / "workspace"
    output = fake_home / "output"
    logs = fake_home / "logs"
    config_toml = fake_codex_home / "config.toml"

    for directory in (fake_codex_home, fake_agents_dir, workspace, output, logs):
        directory.mkdir(parents=True, exist_ok=True)

    config_toml.write_text(
        "\n".join(
            [
                'approval_policy = "never"',
                'sandbox_mode = "read-only"',
                "# Network access is disabled by sandbox policy in plan-only mode.",
                "# No real tokens or real HOME should be mounted.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    target_skill = fake_agents_dir / skill_name
    if target_skill.exists():
        shutil.rmtree(target_skill)
    _copy_tree_no_symlinks(skill, target_skill, warnings)

    paths = CodexSandboxPaths(
        fake_home=str(fake_home),
        fake_codex_home=str(fake_codex_home),
        fake_agents_dir=str(fake_agents_dir),
        sample_mount=str(target_skill),
        output_dir=str(output),
        logs_dir=str(logs),
        config_toml_path=str(config_toml),
        warnings=warnings,
    )
    result = paths.to_dict()
    (base / "fake_home_layout.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
