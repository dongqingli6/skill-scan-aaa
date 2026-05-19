from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import sinkhole_policy


class InMemorySinkhole:
    """Controlled sinkhole event recorder; it never forwards requests."""

    def __init__(self, sample: str, round_id: int, canary_markers: list[str] | None = None) -> None:
        self.sample = sample
        self.round_id = round_id
        self.canary_markers = canary_markers or []
        self.requests: list[dict[str, Any]] = []

    def record_request(self, *, method: str, url: str, headers: dict[str, str] | None = None, body: str = "") -> dict[str, Any]:
        policy = sinkhole_policy.evaluate_sinkhole_destination(url)
        event = {
            "time": datetime.now(timezone.utc).isoformat(),
            "sample": self.sample,
            "round": self.round_id,
            "method": method.upper(),
            "host": policy["host"],
            "path": _path_from_url(url),
            "headers": sinkhole_policy.redact_headers(headers or {}),
            "body_preview": body[:500],
            "honeypot_present": sinkhole_policy.contains_honeypot(body, self.canary_markers),
            "allowed_local_sinkhole": bool(policy["allowed"]),
            "forwarded_external": False,
            "policy_reason": policy["reason"],
        }
        self.requests.append(event)
        return event


def _path_from_url(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.path or "/"
