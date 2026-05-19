from __future__ import annotations

from urllib.parse import urlparse


LOCAL_SINKHOLE_HOSTS = {"127.0.0.1", "localhost", "sinkhole.local", "fake-sinkhole.local"}
FORBIDDEN_HOSTS = {"0.0.0.0", "::", "169.254.169.254"}


def evaluate_sinkhole_destination(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return {"allowed": False, "reason": "missing host", "host": host}
    if host in FORBIDDEN_HOSTS:
        return {"allowed": False, "reason": "forbidden host", "host": host}
    if host not in LOCAL_SINKHOLE_HOSTS:
        return {"allowed": False, "reason": "destination is not controlled local sinkhole", "host": host}
    return {"allowed": True, "reason": "controlled local sinkhole destination", "host": host}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if lowered in {"authorization", "x-api-key", "cookie"}:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value[:200]
    return redacted


def contains_honeypot(body: str, canary_markers: list[str]) -> bool:
    return any(marker and marker in body for marker in canary_markers)
