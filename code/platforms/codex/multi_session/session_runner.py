from __future__ import annotations

from pathlib import Path
from typing import Any

import session_policy


def run_controlled_sessions(sample: str, rounds: int, fake_home: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for item in session_policy.session_plan(rounds):
        decision = session_policy.evaluate_session_command(str(item["command"]))
        events.append(
            {
                "sample": sample,
                "session_id": item["session_id"],
                "round_id": item["round_id"],
                "command": item["command"],
                "fake_home": str(fake_home),
                "fake_home_reused": item["fake_home_reused"],
                "allowed": decision["allowed"],
                "policy_reason": decision["reason"],
                "skill_executed": False,
                "metadata_only_simulation": True,
            }
        )
    return events
