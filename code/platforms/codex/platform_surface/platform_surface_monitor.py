from __future__ import annotations

from typing import Any

import platform_surface_policy


def monitor_platform_surface(sample: str, observations: list[dict[str, str]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for observation in observations:
        operation = observation.get("operation", "read")
        target = observation.get("target", "")
        decision = platform_surface_policy.classify_platform_touch(target, operation)
        if decision["platform_config_touched"]:
            events.append(
                {
                    "sample": sample,
                    "operation": operation,
                    "target": target,
                    "platform_config_touched": True,
                    "touched_items": decision["matched_items"],
                    "policy_impact": decision["severity"],
                }
            )
    return events
