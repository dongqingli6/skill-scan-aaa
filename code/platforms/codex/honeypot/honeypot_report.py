from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_honeypot_events(events: list[dict[str, Any]], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "honeypot_events.json").write_text(json.dumps(events, indent=2, sort_keys=True) + "\n", encoding="utf-8")
