from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from sub_memory.metrics import MetricsLogger, estimate_tokens_from_text


class MetricsTests(unittest.TestCase):
    def test_estimate_tokens_from_text(self) -> None:
        self.assertEqual(estimate_tokens_from_text(""), 0)
        self.assertGreaterEqual(estimate_tokens_from_text("alpha beta gamma"), 1)

    def test_logger_prunes_old_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "metrics.jsonl"
            old_record = {
                "timestamp": (
                    datetime.now(timezone.utc) - timedelta(days=31)
                ).isoformat(),
                "event_type": "old",
            }
            recent_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "recent",
            }
            log_path.write_text(
                json.dumps(old_record, ensure_ascii=False)
                + "\n"
                + json.dumps(recent_record, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )

            logger = MetricsLogger(log_path, retention_days=30)
            logger.log_event("fresh", {"value": 1})

            lines = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [line["event_type"] for line in lines]

            self.assertNotIn("old", event_types)
            self.assertIn("recent", event_types)
            self.assertIn("fresh", event_types)


if __name__ == "__main__":
    unittest.main()
