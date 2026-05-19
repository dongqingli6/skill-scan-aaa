from __future__ import annotations

from pathlib import Path
from typing import Any

import behavior_evidence_loader
import claim_extractor
import divergence_policy


DEFAULT_REAL_SKILLS = [
    "implementation-guide.zip",
    "logging-best-practices.zip",
    "val-town-cli.zip",
    "ideation.zip",
    "react-effect-patterns.zip",
]


def analyze_doc_behavior_divergence(repo_root: Path, inbox: Path, sample_names: list[str] | None = None) -> dict[str, Any]:
    samples = sample_names or list(DEFAULT_REAL_SKILLS)
    evidence_bundle = behavior_evidence_loader.load_behavior_evidence(repo_root, samples)
    results: list[dict[str, Any]] = []

    for sample_name in samples:
        archive_path = inbox / sample_name
        if archive_path.exists():
            claims = claim_extractor.extract_claims_from_archive(archive_path)
        else:
            claims = claim_extractor.extract_claims_from_text("", archive_name=sample_name, skill_member=None)
        sample_evidence = evidence_bundle["samples"].get(sample_name, {})
        findings = divergence_policy.classify_divergences(claims, sample_evidence)
        summary = divergence_policy.summarize_divergence(findings, sample_evidence)
        results.append(
            {
                "archive_name": sample_name,
                "claims": claims,
                "evidence": sample_evidence,
                "divergence_findings": findings,
                "summary": summary,
                "final_recommendation": _recommendation(summary),
            }
        )

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
    decisions = {"blocked": 0, "manual_review": 0, "note": 0, "consistent": 0}
    for result in results:
        severity = result["summary"]["divergence_highest"]
        counts[severity] = counts.get(severity, 0) + 1
        decision = result["summary"]["decision"]
        decisions[decision] = decisions.get(decision, 0) + 1

    return {
        "stage": "Big Stage 26 Document-Behavior Divergence Analysis Layer",
        "mode": "static_existing_evidence_only",
        "total_samples": len(results),
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "network_enabled": False,
        "real_api_called": False,
        "evidence_missing": evidence_bundle["evidence_missing"] or any(not (inbox / name).exists() for name in samples),
        "missing_sources": evidence_bundle["missing_sources"],
        "divergence_counts": counts,
        "decision_counts": decisions,
        "results": results,
        "final_status": "pass",
    }


def _recommendation(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    if decision == "blocked":
        return "HIGH / CRITICAL divergence: blocked pending human security review."
    if decision == "manual_review":
        return "MEDIUM divergence: manual review required before any later activation."
    if decision == "note":
        return "LOW divergence: note for reviewer; no automatic execution approval."
    return "No document-behavior divergence found in existing evidence; existing risk gates still apply."
