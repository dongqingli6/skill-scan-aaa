from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

try:
    import sqlite_vec  # noqa: F401
except ImportError:  # pragma: no cover - depends on native extension
    SQLITE_VEC_AVAILABLE = False
else:
    SQLITE_VEC_AVAILABLE = True

from http.server import ThreadingHTTPServer

from sub_memory.config import Settings
from sub_memory.service import MemoryService
from sub_memory.web import build_handler
from tests.test_memory_store import FakeEmbedder


@unittest.skipUnless(SQLITE_VEC_AVAILABLE, "sqlite-vec is required for this test")
class WebTests(unittest.TestCase):
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
        self.service = MemoryService.from_settings(self.settings, embedder=FakeEmbedder())
        self.first = self.service.store_memory("alpha", "first")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(self.service))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.service.close()
        self.temp_dir.cleanup()

    def test_status_and_ui_routes(self) -> None:
        base_url = f"http://127.0.0.1:{self.server.server_port}"
        status_raw = urlopen(base_url + "/api/status").read().decode("utf-8")
        self.assertIn('"node_count": 1', status_raw)

        ui_raw = urlopen(base_url + "/ui").read().decode("utf-8")
        self.assertIn("[ㄱ] 기억 시각화", ui_raw)

        graph_ui_raw = urlopen(base_url + f"/ui/graph/{self.first['node_id']}").read().decode("utf-8")
        self.assertIn("선택 기억", graph_ui_raw)
        self.assertIn("다시 그리기", graph_ui_raw)
        self.assertIn("branch-controls", graph_ui_raw)
        self.assertIn("접기", graph_ui_raw)

    def test_graph_api_exposes_parent_ids(self) -> None:
        second = self.service.store_memory("beta", "second")
        self.service.store_memory("gamma", "third")

        base_url = f"http://127.0.0.1:{self.server.server_port}"
        raw = urlopen(base_url + f"/api/graph/{self.first['node_id']}?depth=2&limit=10").read().decode("utf-8")
        self.assertIn(f'"center_node_id": "{self.first["node_id"]}"', raw)
        self.assertIn('"parent_id": null', raw)
        self.assertIn(f'"parent_id": "{self.first["node_id"]}"', raw)

    def test_neuralizer_route_deletes_memory(self) -> None:
        base_url = f"http://127.0.0.1:{self.server.server_port}"
        request = Request(
            base_url + f"/api/neuralize/{self.first['node_id']}",
            method="POST",
        )
        raw = urlopen(request).read().decode("utf-8")
        self.assertIn('"status": "deleted"', raw)

        status_raw = urlopen(base_url + "/api/status").read().decode("utf-8")
        self.assertIn('"node_count": 0', status_raw)


if __name__ == "__main__":
    unittest.main()
