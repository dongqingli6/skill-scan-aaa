#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess


DEFAULT_REPO_URL = "https://github.com/TODOTODoTOdoTodotodo/sub-memory-bootstrap.git"
DEFAULT_REPO_REF = "main"
REQUIRED_FILES = ("requirements.txt", "pyproject.toml", "mcp_server.py", ".env.example")


def default_codex_home() -> Path:
    return (Path.home() / ".codex").resolve()


def has_required_files(path: Path) -> bool:
    return all((path / name).exists() for name in REQUIRED_FILES)


def describe_missing_files(path: Path) -> str:
    missing = [name for name in REQUIRED_FILES if not (path / name).exists()]
    return ", ".join(missing)


def find_repo_root(start: Path) -> Path | None:
    candidate = start.resolve()
    for current in (candidate, *candidate.parents):
        if has_required_files(current):
            return current
    return None


def is_jetbrains_managed_codex_home(path: Path) -> bool:
    parts = path.parts
    return "JetBrains" in parts and "aia" in parts and "codex" in parts


def resolve_codex_home() -> Path:
    override = os.getenv("CODEX_HOME")
    if override:
        resolved = Path(override).expanduser().resolve()
        if not is_jetbrains_managed_codex_home(resolved):
            return resolved
    return default_codex_home()


def default_repo_dir(codex_home: Path) -> Path:
    return codex_home / "repos" / "sub-memory-bootstrap"


def ensure_repo_checkout(
    repo_dir: Path,
    *,
    repo_url: str,
    repo_ref: str,
) -> Path:
    repo_dir = repo_dir.expanduser().resolve()

    if has_required_files(repo_dir):
        return repo_dir

    if repo_dir.exists():
        raise RuntimeError(
            "Managed checkout already exists but is incomplete at "
            f"{repo_dir}: missing {describe_missing_files(repo_dir)}"
        )

    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            repo_ref,
            repo_url,
            str(repo_dir),
        ],
        check=True,
    )

    if not has_required_files(repo_dir):
        raise RuntimeError(
            "Cloned repository is missing required files at "
            f"{repo_dir}: {describe_missing_files(repo_dir)}"
        )

    return repo_dir


def resolve_project_dir(
    project_dir: Path | None,
    *,
    script_dir: Path | None = None,
    repo_url: str = DEFAULT_REPO_URL,
    repo_ref: str = DEFAULT_REPO_REF,
    managed_repo_dir: Path | None = None,
) -> Path:
    if project_dir is not None:
        candidate = project_dir.expanduser().resolve()
        if not has_required_files(candidate):
            raise RuntimeError(
                "Target project is missing required files: "
                f"{describe_missing_files(candidate)}"
            )
        return candidate

    start = (script_dir or Path(__file__).resolve().parent).resolve()
    repo_root = find_repo_root(start)
    if repo_root is not None:
        return repo_root

    codex_home = resolve_codex_home()
    repo_dir = managed_repo_dir or default_repo_dir(codex_home)
    return ensure_repo_checkout(
        repo_dir,
        repo_url=repo_url,
        repo_ref=repo_ref,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve a usable sub-memory repository root. If the skill was installed "
            "without the full repository, clone a managed checkout into CODEX_HOME."
        )
    )
    parser.add_argument(
        "--project-dir",
        help="Explicit repository root to use instead of auto resolution.",
    )
    parser.add_argument(
        "--repo-url",
        default=os.getenv("SUB_MEMORY_REPO_URL", DEFAULT_REPO_URL),
        help="Git URL used when a managed checkout must be cloned.",
    )
    parser.add_argument(
        "--ref",
        default=os.getenv("SUB_MEMORY_REPO_REF", DEFAULT_REPO_REF),
        help="Git ref used when a managed checkout must be cloned.",
    )
    parser.add_argument(
        "--managed-repo-dir",
        help="Override the CODEX_HOME-managed repository checkout path.",
    )
    args = parser.parse_args()

    resolved = resolve_project_dir(
        Path(args.project_dir) if args.project_dir else None,
        repo_url=args.repo_url,
        repo_ref=args.ref,
        managed_repo_dir=Path(args.managed_repo_dir) if args.managed_repo_dir else None,
    )
    print(resolved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
