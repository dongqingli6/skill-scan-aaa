#!/usr/bin/env python3
"""Static-only Codex Agent Skill scanner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

CODE_ROOT = Path(__file__).resolve().parents[2]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from platforms.codex.locator import find_codex_skills
from platforms.codex.rules.codex_rules import classify_findings, scan_codex_skill


SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def _empty_counts() -> Dict[str, int]:
    return {severity: 0 for severity in SEVERITIES}


def build_static_scan_result(root: str | Path) -> Dict[str, Any]:
    """Scan a caller-provided root and return a JSON-compatible result."""
    root_path = Path(root).expanduser().resolve()
    records = find_codex_skills(root_path)

    skills: List[Dict[str, Any]] = []
    severity_counts = _empty_counts()
    total_findings = 0

    for record in records:
        findings = scan_codex_skill(record)
        classification = classify_findings(findings)
        total_findings += len(findings)
        for finding in findings:
            severity = finding.get("severity", "LOW")
            if severity in severity_counts:
                severity_counts[severity] += 1

        record.classification = classification["classification"]
        record.static_findings = findings
        record.severity = classification["severity"]
        record.confidence = classification["confidence"]

        skills.append(
            {
                "skill_name": record.skill_name,
                "source_path": record.source_path,
                "skill_md_path": record.skill_md_path,
                "agents_md_path": record.agents_md_path,
                "openai_yaml_path": record.openai_yaml_path,
                "scripts_paths": record.scripts_paths,
                "findings": findings,
                "classification": record.classification,
                "severity": record.severity,
                "confidence": record.confidence,
            }
        )

    return {
        "platform": "codex",
        "root": str(root_path),
        "summary": {
            "total_skills": len(skills),
            "total_findings": total_findings,
            "by_severity": severity_counts,
        },
        "skills": skills,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Static-only Codex skill scanner")
    parser.add_argument("--root", required=True, help="Caller-provided root to scan")
    parser.add_argument("--output", required=True, help="JSON output path")
    args = parser.parse_args()

    result = build_static_scan_result(args.root)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote Codex static scan results: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
