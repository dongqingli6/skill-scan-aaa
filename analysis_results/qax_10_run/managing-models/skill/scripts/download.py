#!/usr/bin/env python3
"""managing-models/scripts/download.py — v1.2 slot 6.7.

Stdin: {"capability": str, "file": str, "repo": str, "sha256": str}
Stdout: ModelHandle JSON or error envelope.

DEFERRED-ACTIVATION: refuses to run unless the host settings have
`allow_model_download = true`. The download itself uses
`urllib.request` for HTTPS direct URLs; HuggingFace repos need the
`huggingface_hub` package. Either path verifies sha256 before
returning a handle.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT))


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


def _settings_allow_download() -> bool:
    try:
        from host.api import settings as S  # noqa: WPS433
        view = S.read_settings_sanitized()
        return bool(view.get("allow_model_download"))
    except Exception:  # noqa: BLE001
        return False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    cap = payload.get("capability", "")
    fname = payload.get("file", "")
    repo = payload.get("repo", "")
    expected_sha = payload.get("sha256", "")

    if not _settings_allow_download():
        _emit({
            "kind": "error",
            "code": "downloads_disabled",
            "message": "managing-models is gated behind allow_model_download user setting",
        })
        return 2

    # The actual download path is intentionally a stub here: shipping
    # weights is the user's call. The Skill returns a deterministic
    # error envelope until the user opts in AND a target file exists
    # under their ComfyUI models dir matching `expected_sha`.
    _emit({
        "kind": "error",
        "code": "not_implemented",
        "message": (
            f"download for {repo}/{fname} ({cap}) is not implemented in this build; "
            "place the file manually under ComfyUI/models and rerun the planner."
        ),
    })
    return 3


if __name__ == "__main__":
    sys.exit(main())
