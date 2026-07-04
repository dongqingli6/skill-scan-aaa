from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

try:
    import sqlite_vec  # noqa: F401
except ImportError:  # pragma: no cover - depends on native extension
    SQLITE_VEC_AVAILABLE = False
else:
    SQLITE_VEC_AVAILABLE = True

from sub_memory.config import Settings
from sub_memory.store import MemoryStore


class FakeEmbedder:
    dimension = 4

    _vectors = {
        "User: alpha\nAssistant: first": [1.0, 0.0, 0.0, 0.0],
        "User: beta\nAssistant: second": [0.9, 0.1, 0.0, 0.0],
        "User: gamma\nAssistant: third": [0.8, 0.2, 0.0, 0.0],
        "alpha": [1.0, 0.0, 0.0, 0.0],
        "beta": [0.9, 0.1, 0.0, 0.0],
        "gamma": [0.8, 0.2, 0.0, 0.0],
    }

    def embed_text(self, text: str) -> list[float]:
        return self._vectors[text]


@unittest.skipUnless(SQLITE_VEC_AVAILABLE, "sqlite-vec is required for this test")
class MemoryStoreTests(unittest.TestCase):
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
        self.store = MemoryStore(self.settings, FakeEmbedder())

    def tearDown(self) -> None:
        self.store.close()
        self.temp_dir.cleanup()

    def test_store_recall_and_reinforce_flow(self) -> None:
        first = self.store.store_memory("alpha", "first")
        second = self.store.store_memory("beta", "second")
        third = self.store.store_memory("gamma", "third")

        self.assertEqual(self.store.count_nodes(), 3)
        self.assertIsNotNone(self.store.get_edge_weight(first["node_id"], second["node_id"]))
        self.assertIsNotNone(self.store.get_edge_weight(second["node_id"], third["node_id"]))

        recalled = self.store.recall_associated_memory("alpha", depth=2)
        recalled_ids = recalled["node_ids"]

        self.assertGreaterEqual(len(recalled_ids), 2)
        self.assertEqual(recalled_ids[0], first["node_id"])

        prior_weight = self.store.get_edge_weight(first["node_id"], second["node_id"])
        assert prior_weight is not None

        reinforced = self.store.reinforce_memory(recalled_ids[:2])
        self.assertEqual(reinforced["status"], "reinforced")

        updated_weight = self.store.get_edge_weight(first["node_id"], second["node_id"])
        assert updated_weight is not None
        self.assertAlmostEqual(updated_weight, prior_weight + 0.1, places=6)

    def test_dashboard_and_graph_queries(self) -> None:
        first = self.store.store_memory("alpha", "first")
        second = self.store.store_memory("beta", "second")
        self.store.store_memory("gamma", "third")

        dashboard = self.store.get_dashboard_stats()
        self.assertEqual(dashboard["node_count"], 3)
        self.assertGreaterEqual(dashboard["edge_count"], 2)
        self.assertEqual(len(dashboard["recent_memories"]), 3)

        memories = self.store.list_memories(query="beta")
        self.assertEqual(len(memories), 1)
        self.assertIn("beta", memories[0]["text"])

        detail = self.store.get_memory(second["node_id"])
        self.assertIsNotNone(detail)

        connected = self.store.get_connected_memories(second["node_id"])
        self.assertGreaterEqual(len(connected), 1)

        graph = self.store.get_graph_subtree(first["node_id"], depth=2, limit=10)
        self.assertEqual(graph["center_node_id"], first["node_id"])
        self.assertGreaterEqual(len(graph["nodes"]), 2)
        self.assertGreaterEqual(len(graph["edges"]), 1)
        center_node = next(node for node in graph["nodes"] if node["node_id"] == first["node_id"])
        self.assertIsNone(center_node["parent_id"])
        child_nodes = [node for node in graph["nodes"] if node["node_id"] != first["node_id"]]
        self.assertTrue(any(node["parent_id"] == first["node_id"] for node in child_nodes))

    def test_delete_memory_removes_only_target_node(self) -> None:
        first = self.store.store_memory("alpha", "first")
        second = self.store.store_memory("beta", "second")
        third = self.store.store_memory("gamma", "third")

        result = self.store.delete_memory(second["node_id"])

        self.assertEqual(result["status"], "deleted")
        self.assertGreaterEqual(result["deleted_connection_count"], 1)
        self.assertEqual(self.store.count_nodes(), 2)
        self.assertIsNone(self.store.get_memory(second["node_id"]))
        self.assertIsNotNone(self.store.get_memory(first["node_id"]))
        self.assertIsNotNone(self.store.get_memory(third["node_id"]))

    def test_store_memory_ignores_stale_last_node_id_after_db_replacement(self) -> None:
        self.store._last_node_id = "missing-node-id"
        result = self.store.store_memory("alpha", "first")

        self.assertEqual(result["status"], "stored")
        self.assertEqual(self.store.count_nodes(), 1)
        self.assertEqual(self.store.count_edges(), 0)

    def test_store_memory_ignores_foreign_key_race_while_linking_previous_node(self) -> None:
        first = self.store.store_memory("alpha", "first")
        self.assertEqual(self.store.count_nodes(), 1)

        original = self.store._upsert_edge_locked

        def raise_once(*args, **kwargs):
            raise sqlite3.IntegrityError("FOREIGN KEY constraint failed")

        self.store._upsert_edge_locked = raise_once  # type: ignore[method-assign]
        try:
            result = self.store.store_memory("beta", "second")
        finally:
            self.store._upsert_edge_locked = original  # type: ignore[method-assign]

        self.assertEqual(result["status"], "stored")
        self.assertEqual(self.store.count_nodes(), 2)
        self.assertEqual(self.store.count_edges(), 0)
        self.assertEqual(self.store._last_node_id, result["node_id"])
        self.assertIsNone(self.store.get_edge_weight(first["node_id"], result["node_id"]))

    def test_graph_query_reloads_after_external_db_restore(self) -> None:
        with sqlite3.connect(self.settings.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                INSERT INTO nodes (id, text, embedding, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                ("node-a", "User: alpha\nAssistant: first", b"\x00" * 16, "2026-04-15T00:00:00+00:00"),
            )
            conn.execute(
                """
                INSERT INTO nodes (id, text, embedding, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                ("node-b", "User: beta\nAssistant: second", b"\x00" * 16, "2026-04-15T00:01:00+00:00"),
            )
            conn.execute(
                """
                INSERT INTO edges (source_id, target_id, weight)
                VALUES (?, ?, ?)
                """,
                ("node-a", "node-b", 1.0),
            )
            conn.commit()

        graph = self.store.get_graph_subtree("node-b", depth=2, limit=10)

        self.assertEqual(graph["center_node_id"], "node-b")
        self.assertEqual(len(graph["nodes"]), 2)
        self.assertEqual(len(graph["edges"]), 1)
