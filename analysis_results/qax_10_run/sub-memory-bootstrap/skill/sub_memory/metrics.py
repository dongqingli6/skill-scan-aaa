from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import threading
from typing import Any


def estimate_tokens_from_text(text: str) -> int:
    collapsed = " ".join(text.split())
    if not collapsed:
        return 0
    return max(1, (len(collapsed) + 2) // 3)


def count_chars(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    return len(json.dumps(value, ensure_ascii=False))


@dataclass(slots=True)
class MetricsLogger:
    log_path: Path
    retention_days: int = 30
    _lock: threading.RLock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **payload,
        }

        line = json.dumps(record, ensure_ascii=False)

        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            self._prune_locked()

    def _prune_locked(self) -> None:
        if self.retention_days < 1 or not self.log_path.exists():
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        kept_lines: list[str] = []

        for raw_line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
                timestamp = datetime.fromisoformat(record["timestamp"])
            except Exception:
                kept_lines.append(raw_line)
                continue

            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            if timestamp >= cutoff:
                kept_lines.append(raw_line)

        self.log_path.write_text(
            ("\n".join(kept_lines) + "\n") if kept_lines else "",
            encoding="utf-8",
        )
