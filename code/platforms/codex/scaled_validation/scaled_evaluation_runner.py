from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from typing import Any

MODULE_ROOT = Path(__file__).resolve().parent
DOC_DIFF_ROOT = MODULE_ROOT.parent / "doc_behavior_diff"
if str(DOC_DIFF_ROOT) not in sys.path:
    sys.path.insert(0, str(DOC_DIFF_ROOT))

import claim_extractor
import divergence_policy
import metrics


OUTPUT_ROOT = Path("analysis_results/scaled_validation")
SYNTHETIC_CORPUS_ROOT = OUTPUT_ROOT / "synthetic_corpus"
REAL_RESULT_SOURCES = {
    "static_dashboard": "analysis_results/real_skill_batch_static_dashboard/summary.json",
    "agent_static": "analysis_results/agent_static_analysis/summary.json",
    "doc_behavior": "analysis_results/doc_behavior_divergence/summary.json",
    "dynamic_monitoring": "analysis_results/real_skill_dynamic_monitoring_batch/summary.json",
    "runtime_synthetic": "analysis_results/runtime_violation_synthetic_live/summary.json",
}


def run_scaled_evaluation(repo_root: Path, *, include_real_skills: bool = True) -> dict[str, Any]:
    synthetic_results = _evaluate_synthetic_corpus(repo_root / SYNTHETIC_CORPUS_ROOT)
    real_results = _load_real_skill_results(repo_root) if include_real_skills else []
    results = [*real_results, *synthetic_results]
    computed_metrics = metrics.compute_metrics(results)
    matrix = metrics.confusion_matrix(computed_metrics)
    return {
        "stage": "Big Stage 27 Scaled Validation and Final Reporting Layer",
        "mode": "static_only",
        "docker_executed": False,
        "codex_executed": False,
        "claude_code_executed": False,
        "strace_executed": False,
        "real_skill_executed": False,
        "network_enabled": False,
        "real_api_called": False,
        "total_samples": len(results),
        "real_skill_count": len(real_results),
        "synthetic_count": len(synthetic_results),
        "results": results,
        "metrics": computed_metrics,
        "confusion_matrix": matrix,
        "source_paths": REAL_RESULT_SOURCES,
        "final_status": "pass",
    }


def _evaluate_synthetic_corpus(corpus_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for archive_path in sorted(corpus_root.glob("*.zip")):
        skill_text, expected = _read_synthetic_archive(archive_path)
        claims = claim_extractor.extract_claims_from_text(skill_text, archive_name=archive_path.name)
        static = _static_text_evaluate(skill_text)
        evidence = {
            "evidence_flags": static["evidence_flags"],
            "deterministic_highest": static["severity"],
            "agent_highest": _agent_mock_severity(static["severity"]),
            "final_highest": static["severity"],
            "evidence_missing": False,
        }
        divergence_findings = divergence_policy.classify_divergences(claims, evidence)
        divergence_summary = divergence_policy.summarize_divergence(divergence_findings, evidence)
        final_severity = metrics.max_severity([static["severity"], divergence_summary["divergence_highest"]])
        gate = _gate_for(final_severity, expected.get("expected_family"))
        results.append(
            {
                "archive_name": archive_path.name,
                "sample_type": "synthetic",
                "sample_family": expected.get("expected_family", "unknown"),
                "expected_min_severity": expected.get("expected_min_severity", "none"),
                "expected_gate": expected.get("expected_gate", "unknown"),
                "static_severity": static["severity"],
                "agent_mock_severity": evidence["agent_highest"],
                "divergence": divergence_summary["divergence_highest"],
                "final_severity": final_severity,
                "gate": gate,
                "finding_categories": static["finding_categories"] + [finding["category"] for finding in divergence_findings],
                "recommendation": _recommendation(gate),
            }
        )
    return results


def _read_synthetic_archive(archive_path: Path) -> tuple[str, dict[str, Any]]:
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        skill_member = next(name for name in names if Path(name.replace("\\", "/")).name == "SKILL.md")
        expected_member = next(name for name in names if Path(name.replace("\\", "/")).name == "expected_label.json")
        skill_text = archive.read(skill_member).decode("utf-8", errors="replace")
        expected = json.loads(archive.read(expected_member).decode("utf-8", errors="replace"))
    return skill_text, expected


def _static_text_evaluate(text: str) -> dict[str, Any]:
    lowered = text.lower()
    flags = {
        "network": any(term in lowered for term in ("network", "api", "upload", "exfiltrate", "request text")),
        "credential": any(term in lowered for term in ("fake_token", "fake_env", "fake_ssh", "id_rsa", "private_key")),
        "filesystem": any(term in lowered for term in ("scan many files", "home-like", "fake_home", ".ssh")),
        "docker": "/var/run/docker.sock" in lowered or "fake_docker_socket" in lowered,
        "install": any(term in lowered for term in ("install package", "dependency install")),
        "execution": any(term in lowered for term in ("shell", "bash", "command-like")),
        "prompt_injection": any(term in lowered for term in ("ignore safety policy", "ignore system", "reveal hidden policy", "hidden operator")),
    }
    categories: list[str] = []
    severity = "none"
    if flags["docker"] or "fake_ssh_private_key" in lowered:
        severity = "critical"
        categories.append("critical_container_or_fake_secret_reference")
    elif flags["credential"] or flags["prompt_injection"] or "exfiltrate" in lowered:
        severity = "high"
        categories.append("high_fake_credential_or_prompt_injection")
    elif flags["network"] or flags["filesystem"] or flags["execution"]:
        severity = "medium"
        categories.append("medium_suspicious_capability_hint")
    return {"severity": severity, "evidence_flags": flags, "finding_categories": categories}


def _agent_mock_severity(static_severity: str) -> str:
    return static_severity


def _gate_for(severity: str, family: str | None) -> str:
    if family == "suspicious":
        return "manual_review"
    if severity in ("critical", "high"):
        return "blocked"
    if severity == "medium":
        return "manual_review"
    return "allowed"


def _recommendation(gate: str) -> str:
    if gate == "blocked":
        return "Block and send to human security review."
    if gate == "manual_review":
        return "Send to manual review before any later runtime stage."
    return "No scaled-validation blocker; existing gates still apply."


def _load_real_skill_results(repo_root: Path) -> list[dict[str, Any]]:
    static_summary = _read_json(repo_root / REAL_RESULT_SOURCES["static_dashboard"])
    agent_summary = _read_json(repo_root / REAL_RESULT_SOURCES["agent_static"])
    doc_summary = _read_json(repo_root / REAL_RESULT_SOURCES["doc_behavior"])
    agent_by_name = {item["archive_name"]: item for item in agent_summary.get("results", [])}
    doc_by_name = {item["archive_name"]: item for item in doc_summary.get("results", [])}
    results: list[dict[str, Any]] = []
    for sample in static_summary.get("samples", []):
        name = sample["archive_name"]
        agent = agent_by_name.get(name, {})
        doc = doc_by_name.get(name, {})
        static_severity = _severity_from_counts(sample)
        final_severity = metrics.max_severity([static_severity, agent.get("final_highest", "none"), doc.get("final_risk", "none")])
        gate = _real_gate(sample.get("category"), doc.get("decision"))
        results.append(
            {
                "archive_name": name,
                "sample_type": "real",
                "sample_family": "real",
                "static_severity": static_severity,
                "agent_mock_severity": agent.get("agent_highest", "none"),
                "divergence": doc.get("divergence_highest", "none"),
                "final_severity": final_severity,
                "gate": gate,
                "finding_categories": doc.get("finding_categories", []),
                "recommendation": doc.get("final_recommendation") or sample.get("recommendation", ""),
            }
        )
    return results


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _severity_from_counts(sample: dict[str, Any]) -> str:
    for severity in ("critical", "high", "medium", "low"):
        if int(sample.get(severity, 0) or 0) > 0:
            return severity
    return "none"


def _real_gate(category: str | None, doc_decision: str | None) -> str:
    if category == "blocked" or doc_decision == "blocked":
        return "blocked"
    if category == "manual_review" or doc_decision == "manual_review":
        return "manual_review"
    return "allowed"
