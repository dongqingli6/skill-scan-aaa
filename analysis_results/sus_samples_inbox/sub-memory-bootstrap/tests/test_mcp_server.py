from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import anyio

try:
    import sqlite_vec  # noqa: F401
except ImportError:  # pragma: no cover - depends on native extension
    SQLITE_VEC_AVAILABLE = False
else:
    SQLITE_VEC_AVAILABLE = True

from sub_memory.config import Settings
from sub_memory.mcp_server import build_mcp_server
from sub_memory.service import MemoryService
from tests.test_memory_store import FakeEmbedder


class FlexibleFakeEmbedder:
    dimension = 4

    def embed_text(self, text: str) -> list[float]:
        seed = sum(ord(ch) for ch in text)
        return [
            float((seed % 7) + 1),
            float((seed % 11) + 1),
            float((seed % 13) + 1),
            float((seed % 17) + 1),
        ]


@unittest.skipUnless(SQLITE_VEC_AVAILABLE, "sqlite-vec is required for this test")
class MCPServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.settings = Settings(
            base_dir=self.base_path,
            db_path=self.base_path / "memory.db",
            openai_api_key=None,
            openai_model="gpt-5-mini",
            embedding_model_name="fake-embedder",
            sqlite_vec_path=None,
            recall_depth=2,
            recall_limit=6,
            compact_after_turns=4,
            compact_keep_recent_turns=2,
            compact_summary_char_limit=2400,
            metrics_log_path=self.base_path / ".sub-memory" / "metrics.jsonl",
            metrics_retention_days=30,
        )
        self.service = MemoryService.from_settings(
            self.settings,
            embedder=FakeEmbedder(),
        )
        self.server = build_mcp_server(self.service, log_level="ERROR")

    def tearDown(self) -> None:
        self.service.close()
        self.temp_dir.cleanup()

    def test_registered_tools_and_store_flow(self) -> None:
        async def run_test() -> None:
            tools = await self.server.list_tools()
            tool_names = {tool.name for tool in tools}
            self.assertEqual(
                tool_names,
                {
                    "recall_associated_memory",
                    "store_memory",
                    "reinforce_memory",
                    "get_memory_status",
                },
            )

            _contents, store_result = await self.server.call_tool(
                "store_memory",
                {"user_text": "alpha", "ai_response": "first"},
            )
            self.assertEqual(store_result["status"], "stored")

            _contents, status_result = await self.server.call_tool(
                "get_memory_status",
                {},
            )
            self.assertEqual(status_result["node_count"], 1)
            self.assertIn("session_context", status_result)
            self.assertEqual(
                status_result["session_context"]["recent_turn_count"],
                1,
            )

        anyio.run(run_test)

    def test_store_and_recall_include_compacted_session_context(self) -> None:
        compact_settings = Settings(
            base_dir=self.base_path,
            db_path=self.base_path / "compact-memory.db",
            openai_api_key=None,
            openai_model="gpt-5-mini",
            embedding_model_name="fake-embedder",
            sqlite_vec_path=None,
            recall_depth=2,
            recall_limit=6,
            compact_after_turns=2,
            compact_keep_recent_turns=1,
            compact_summary_char_limit=2400,
            metrics_log_path=self.base_path / ".sub-memory" / "compact-metrics.jsonl",
            metrics_retention_days=30,
        )
        compact_service = MemoryService.from_settings(
            compact_settings,
            embedder=FlexibleFakeEmbedder(),
        )
        compact_server = build_mcp_server(compact_service, log_level="ERROR")

        async def run_test() -> None:
            _contents, first_store = await compact_server.call_tool(
                "store_memory",
                {"user_text": "first request", "ai_response": "first answer"},
            )
            self.assertFalse(first_store["session_context"]["compacted"])

            _contents, second_store = await compact_server.call_tool(
                "store_memory",
                {"user_text": "second request", "ai_response": "second answer"},
            )
            self.assertTrue(second_store["session_context"]["compacted"])
            self.assertIn(
                "first request",
                second_store["session_context"]["summary"],
            )
            self.assertEqual(
                second_store["session_context"]["recent_turn_count"],
                1,
            )

            _contents, recall_result = await compact_server.call_tool(
                "recall_associated_memory",
                {"query": "second request", "depth": 2},
            )
            self.assertIn("session_context", recall_result)
            self.assertIn(
                "Compact session summary:",
                recall_result["session_context"]["rendered"],
            )
            self.assertIn(
                "second request",
                recall_result["session_context"]["rendered"],
            )

        try:
            anyio.run(run_test)
        finally:
            compact_service.close()
