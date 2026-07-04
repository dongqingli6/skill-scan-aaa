from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "sub-memory-bootstrap"
    / "scripts"
    / "ensure_repo_checkout.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "ensure_repo_checkout",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnsureRepoCheckoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_repo(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        for name in self.module.REQUIRED_FILES:
            (path / name).write_text("", encoding="utf-8")
        return path

    def test_resolve_project_dir_uses_explicit_repo(self) -> None:
        repo_dir = self.create_repo(self.root / "explicit")

        resolved = self.module.resolve_project_dir(repo_dir)

        self.assertEqual(resolved, repo_dir.resolve())

    def test_resolve_project_dir_discovers_repo_from_script_ancestors(self) -> None:
        repo_dir = self.create_repo(self.root / "installed-skill")
        script_dir = repo_dir / "skills" / "sub-memory-bootstrap" / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)

        resolved = self.module.resolve_project_dir(None, script_dir=script_dir)

        self.assertEqual(resolved, repo_dir.resolve())

    def test_resolve_project_dir_clones_managed_checkout_when_skill_is_nested_only(self) -> None:
        codex_home = self.root / "codex-home"
        script_dir = codex_home / "skills" / "sub-memory-bootstrap" / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        managed_repo_dir = codex_home / "repos" / "sub-memory-bootstrap"
        clone_calls: list[list[str]] = []

        def fake_run(cmd: list[str], check: bool) -> None:
            self.assertTrue(check)
            clone_calls.append(cmd)
            self.create_repo(managed_repo_dir)

        with patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
            with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                resolved = self.module.resolve_project_dir(None, script_dir=script_dir)

        self.assertEqual(resolved, managed_repo_dir.resolve())
        self.assertEqual(len(clone_calls), 1)
        self.assertEqual(clone_calls[0][:6], ["git", "clone", "--depth", "1", "--branch", "main"])
        self.assertEqual(clone_calls[0][6], self.module.DEFAULT_REPO_URL)
        self.assertEqual(clone_calls[0][7], str(managed_repo_dir.resolve()))

    def test_resolve_codex_home_ignores_jetbrains_managed_override(self) -> None:
        jetbrains_codex_home = (
            self.root / "Library" / "Caches" / "JetBrains" / "IntelliJIdea2025.3" / "aia" / "codex"
        )

        with patch.dict(os.environ, {"CODEX_HOME": str(jetbrains_codex_home)}):
            with patch.object(self.module.Path, "home", return_value=self.root):
                resolved = self.module.resolve_codex_home()

        self.assertEqual(resolved, (self.root / ".codex").resolve())

    def test_resolve_project_dir_prefers_user_codex_home_over_jetbrains_cache(self) -> None:
        jetbrains_codex_home = (
            self.root / "Library" / "Caches" / "JetBrains" / "IntelliJIdea2025.3" / "aia" / "codex"
        )
        script_dir = jetbrains_codex_home / "skills" / "sub-memory-bootstrap" / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        managed_repo_dir = self.root / ".codex" / "repos" / "sub-memory-bootstrap"
        clone_calls: list[list[str]] = []

        def fake_run(cmd: list[str], check: bool) -> None:
            self.assertTrue(check)
            clone_calls.append(cmd)
            self.create_repo(managed_repo_dir)

        with patch.dict(os.environ, {"CODEX_HOME": str(jetbrains_codex_home)}):
            with patch.object(self.module.Path, "home", return_value=self.root):
                with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                    resolved = self.module.resolve_project_dir(None, script_dir=script_dir)

        self.assertEqual(resolved, managed_repo_dir.resolve())
        self.assertEqual(len(clone_calls), 1)
        self.assertEqual(clone_calls[0][7], str(managed_repo_dir.resolve()))


if __name__ == "__main__":
    unittest.main()
