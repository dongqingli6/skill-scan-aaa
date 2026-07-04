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
    / "configure_codex_project.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "configure_codex_project",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConfigureCodexProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)
        self.runtime_dir = self.project_dir / "global-runtime"
        (self.project_dir / "requirements.txt").write_text("", encoding="utf-8")
        (self.project_dir / "pyproject.toml").write_text("", encoding="utf-8")
        (self.project_dir / "mcp_server.py").write_text("", encoding="utf-8")
        (self.project_dir / ".env.example").write_text("OPENAI_MODEL=gpt-5-mini\n", encoding="utf-8")
        mcp_entrypoint = self.project_dir / ".venv" / "bin" / "sub-memory-mcp"
        mcp_entrypoint.parent.mkdir(parents=True, exist_ok=True)
        mcp_entrypoint.write_text("#!/bin/sh\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_configure_project_creates_codex_config_and_agents(self) -> None:
        with patch.dict(os.environ, {"SUB_MEMORY_BASE_DIR": str(self.runtime_dir)}):
            paths = self.module.configure_project(self.project_dir)

        config_text = paths["config_path"].read_text(encoding="utf-8")
        agents_text = paths["agents_path"].read_text(encoding="utf-8")

        self.assertIn("[mcp_servers.sub_memory]", config_text)
        self.assertIn('url = "http://127.0.0.1:8766/mcp"', config_text)
        self.assertIn("## sub_memory MCP", agents_text)
        self.assertIn("get_memory_status", agents_text)
        self.assertIn("compact the active thread", agents_text)
        self.assertTrue(self.runtime_dir.is_dir())
        self.assertTrue((self.runtime_dir / ".env").exists())
        self.assertEqual(paths["runtime_dir"], self.runtime_dir.resolve())

    def test_configure_project_preserves_existing_content(self) -> None:
        config_path = self.project_dir / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            '[profiles.default]\nmodel = "gpt-5"\n\n'
            '[mcp_servers.sub_memory]\nurl = "http://127.0.0.1:9000/mcp"\n',
            encoding="utf-8",
        )
        agents_path = self.project_dir / "AGENTS.md"
        agents_path.write_text(
            "# Custom Notes\n\nDo not remove this section.\n",
            encoding="utf-8",
        )

        with patch.dict(os.environ, {"SUB_MEMORY_BASE_DIR": str(self.runtime_dir)}):
            self.module.configure_project(self.project_dir)

        config_text = config_path.read_text(encoding="utf-8")
        agents_text = agents_path.read_text(encoding="utf-8")

        self.assertIn('[profiles.default]\nmodel = "gpt-5"', config_text)
        self.assertEqual(config_text.count("[mcp_servers.sub_memory]"), 1)
        self.assertIn('url = "http://127.0.0.1:8766/mcp"', config_text)
        self.assertIn("# Custom Notes", agents_text)
        self.assertIn("Do not remove this section.", agents_text)
        self.assertIn("## sub_memory MCP", agents_text)
        self.assertIn("compact the active thread", agents_text)
