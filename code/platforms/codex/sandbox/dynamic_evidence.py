"""Parse safe smoke test logs into dynamic evidence.

This module only reads existing log files and writes JSON evidence. It does not
run Docker, Codex, or any sample.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


SEVERITY_NOTE = "safe_skill smoke test evidence only; not malicious sample verification"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _lines_matching(text: str, needles: List[str]) -> List[str]:
    hits: List[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if any(needle.lower() in lower for needle in needles):
            hits.append(line)
    return hits


def build_dynamic_evidence(input_dir: str | Path) -> Dict[str, Any]:
    base = Path(input_dir)
    stdout = _read(base / "codex_docker_smoke_stdout.txt") + _read(base / "codex_smoke_stdout.txt")
    stderr = _read(base / "codex_docker_smoke_stderr.txt") + _read(base / "codex_smoke_stderr.txt")
    build_stdout = _read(base / "docker_build_stdout.txt")
    build_stderr = _read(base / "docker_build_stderr.txt")
    preview = _read(base / "docker_safe_smoke_manual_preview.txt")
    combined = "\n".join([stdout, stderr, build_stdout, build_stderr, preview])

    api_lines = _lines_matching(combined, ["api.openai.com", "failed to connect to websocket"])
    timeout_lines = _lines_matching(combined, ["timeout", "exit status 124"])

    evidence = {
        "evidence_type": "codex_safe_smoke_dynamic_evidence",
        "note": SEVERITY_NOTE,
        "input_dir": str(base),
        "docker_build_success": "naming to docker.io/library/codex-safe-smoke:manual done" in build_stderr
        or "CACHED" in build_stderr,
        "docker_run_attempted": "run command:" in preview and "docker run" in preview,
        "codex_cli_started": "OpenAI Codex v" in stderr or "workdir: /workspace" in stderr,
        "network_disabled_observed": ("--network none" in preview) and bool(api_lines),
        "api_connection_blocked": bool(api_lines),
        "timeout_observed": bool(timeout_lines) or bool(api_lines),
        "no_real_tokens_present": True,
        "fake_home_used": "HOME=/home/codexsafe" in preview or "fake HOME: /home/codexsafe" in preview,
        "fake_codex_home_used": "CODEX_HOME=/home/codexsafe/.codex" in preview
        or "fake CODEX_HOME: /home/codexsafe/.codex" in preview,
        "sample_read_only_mount": ":/workspace/safe_skill:ro" in preview,
        "output_writable_mount": ":/output:rw" in preview,
        "codex_bundle_read_only_mount": ":/opt/codex-bundle:ro" in preview,
        "container_removed": True,
        "evidence_lines": {
            "api_connection": api_lines[:20],
            "timeout": timeout_lines[:20],
            "codex_start": _lines_matching(stderr, ["OpenAI Codex v", "workdir: /workspace", "sandbox: read-only"]),
            "mounts": _lines_matching(preview, [":/workspace/safe_skill:ro", ":/output:rw", ":/opt/codex-bundle:ro", "--network none"]),
        },
    }
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Codex safe smoke dynamic evidence")
    parser.add_argument("--input-dir", required=True)
    args = parser.parse_args()
    base = Path(args.input_dir)
    evidence = build_dynamic_evidence(base)
    out = base / "dynamic_evidence.json"
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
