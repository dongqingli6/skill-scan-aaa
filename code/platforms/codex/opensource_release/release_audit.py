from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SENSITIVE_SUFFIXES = (".pem", ".key", ".gz", ".tar.gz", ".zip")
SENSITIVE_NAMES = (".env", "id_rsa", "id_rsa.pub")
SENSITIVE_NAME_PARTS = ("token", "secret", "unredacted", "raw", "inbox", "real_skill")
CONTENT_MARKERS = ("/home/empty", "OPENAI_API_KEY=", "ANTHROPIC_API_KEY=", "GITHUB_TOKEN=", "BEGIN OPENSSH PRIVATE KEY")


def run_release_audit(repo_root: Path, output_root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(repo_root).as_posix()
        lowered = rel.lower()
        reasons = []
        if path.name in SENSITIVE_NAMES:
            reasons.append("sensitive filename")
        if lowered.endswith(SENSITIVE_SUFFIXES):
            reasons.append("sensitive archive/key suffix")
        if any(part in lowered for part in SENSITIVE_NAME_PARTS):
            reasons.append("sensitive filename or directory marker")
        if rel.startswith("analysis_results/") and any(part in lowered for part in ("raw", "inbox", "real_skill", "unredacted")):
            reasons.append("analysis_results may contain unredacted sample material")
        if _contains_marker(path):
            reasons.append("content marker requires sanitization")
        if reasons:
            findings.append({"path": rel, "reasons": sorted(set(reasons)), "public_recommendation": "exclude_or_sanitize"})
    summary = {
        "stage": "Big Stage 30 Open Source Release Audit",
        "scanned_files": sum(1 for item in repo_root.rglob("*") if item.is_file()),
        "findings_count": len(findings),
        "findings": findings,
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "network_enabled": False,
        "real_api_called": False,
        "files_deleted": False,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "release_audit.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / "release_audit.md").write_text(_audit_md(summary), encoding="utf-8")
    return summary


def _contains_marker(path: Path) -> bool:
    if path.stat().st_size > 2_000_000:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(marker in text for marker in CONTENT_MARKERS)


def _audit_md(summary: dict[str, Any]) -> str:
    lines = ["# Open Source Release Audit", "", f"- Findings: `{summary['findings_count']}`", "- Files deleted: `false`", ""]
    for finding in summary["findings"][:200]:
        lines.append(f"- `{finding['path']}`: {', '.join(finding['reasons'])}")
    if len(summary["findings"]) > 200:
        lines.append(f"- ... {len(summary['findings']) - 200} additional findings omitted from markdown summary")
    lines.append("")
    return "\n".join(lines)
