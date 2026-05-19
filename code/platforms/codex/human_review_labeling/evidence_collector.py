from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SOURCE_PATHS = {
    "static_dashboard": "analysis_results/real_skill_batch_static_dashboard/summary.json",
    "agent_static": "analysis_results/agent_static_analysis/summary.json",
    "doc_behavior": "analysis_results/doc_behavior_divergence/summary.json",
    "dynamic_monitoring": "analysis_results/real_skill_dynamic_monitoring_batch/summary.json",
    "runtime_synthetic": "analysis_results/runtime_violation_synthetic_live/summary.json",
    "controlled_activation": "analysis_results/controlled_skill_activation/summary.json",
    "scaled_validation": "analysis_results/scaled_validation/summary.json",
    "stage28_dynamic": "analysis_results/controlled_sinkhole_dynamic/summary.json",
    "stage28_evidence": "analysis_results/controlled_sinkhole_dynamic/dynamic_evidence.json",
    "stage28_sinkhole": "analysis_results/controlled_sinkhole_dynamic/sinkhole_requests.json",
    "stage28_honeypot": "analysis_results/controlled_sinkhole_dynamic/honeypot_events.json",
    "stage28_sessions": "analysis_results/controlled_sinkhole_dynamic/multi_session_report.json",
    "stage28_platform": "analysis_results/controlled_sinkhole_dynamic/platform_surface_events.json",
}


def collect_evidence(repo_root: Path, *, include_real: bool = True, include_synthetic: bool = True) -> dict[str, Any]:
    sources = {name: _read_json(repo_root / rel) for name, rel in SOURCE_PATHS.items()}
    samples: dict[str, dict[str, Any]] = {}
    _merge_scaled(samples, sources.get("scaled_validation", {}), include_real, include_synthetic)
    _merge_static(samples, sources.get("static_dashboard", {}))
    _merge_agent(samples, sources.get("agent_static", {}))
    _merge_doc(samples, sources.get("doc_behavior", {}))
    _merge_stage28(samples, sources)
    missing = [rel for rel in SOURCE_PATHS.values() if not (repo_root / rel).exists()]
    for sample in samples.values():
        sample["evidence_missing"] = bool(missing) or not sample.get("evidence_paths")
    return {"samples": list(samples.values()), "missing_sources": missing, "evidence_missing": bool(missing), "source_paths": SOURCE_PATHS}


def _base(sample: str, source_type: str = "unknown", family: str = "") -> dict[str, Any]:
    return {
        "sample_name": sample,
        "source_type": source_type,
        "sample_family": family,
        "static_findings": [],
        "agent_findings": [],
        "divergence_findings": [],
        "runtime_findings": [],
        "sinkhole_events": [],
        "honeypot_events": [],
        "multi_session_events": [],
        "platform_surface_events": [],
        "risk_summary": {"severity": "NONE"},
        "existing_gate_decision": "",
        "evidence_paths": [],
        "evidence_missing": False,
    }


def _ensure(samples: dict[str, dict[str, Any]], name: str, source_type: str = "unknown", family: str = "") -> dict[str, Any]:
    if name not in samples:
        samples[name] = _base(name, source_type, family)
    if source_type != "unknown":
        samples[name]["source_type"] = source_type
    if family:
        samples[name]["sample_family"] = family
    return samples[name]


def _merge_scaled(samples: dict[str, dict[str, Any]], data: dict[str, Any], include_real: bool, include_synthetic: bool) -> None:
    for item in data.get("results", []):
        source_type = item.get("sample_type", "unknown")
        if source_type == "real" and not include_real:
            continue
        if source_type == "synthetic" and not include_synthetic:
            continue
        sample = _ensure(samples, item["archive_name"], source_type, item.get("sample_family", ""))
        sample["risk_summary"]["severity"] = _norm_sev(item.get("final_severity", "NONE"))
        sample["existing_gate_decision"] = item.get("gate", "")
        sample["evidence_paths"].append("analysis_results/scaled_validation/summary.json")


def _merge_static(samples: dict[str, dict[str, Any]], data: dict[str, Any]) -> None:
    for item in data.get("samples", []):
        sample = _ensure(samples, item["archive_name"], "real", "real")
        sample["static_findings"].extend(item.get("high_findings", []))
        sample["risk_summary"]["static_severity"] = _highest_from_counts(item)
        sample["evidence_paths"].append("analysis_results/real_skill_batch_static_dashboard/summary.json")


def _merge_agent(samples: dict[str, dict[str, Any]], data: dict[str, Any]) -> None:
    for item in data.get("results", []):
        sample = _ensure(samples, item["archive_name"], "real", "real")
        sample["agent_findings"].append(item)
        sample["risk_summary"]["agent_severity"] = _norm_sev(item.get("final_highest", "NONE"))
        sample["evidence_paths"].append("analysis_results/agent_static_analysis/summary.json")


def _merge_doc(samples: dict[str, dict[str, Any]], data: dict[str, Any]) -> None:
    for item in data.get("results", []):
        sample = _ensure(samples, item["archive_name"], "real", "real")
        sample["divergence_findings"].extend(item.get("finding_categories", []))
        sample["risk_summary"]["divergence_severity"] = _norm_sev(item.get("divergence_highest", "NONE"))
        sample["evidence_paths"].append("analysis_results/doc_behavior_divergence/summary.json")


def _merge_stage28(samples: dict[str, dict[str, Any]], sources: dict[str, Any]) -> None:
    for item in sources.get("stage28_evidence", []) if isinstance(sources.get("stage28_evidence"), list) else []:
        source_type = "real" if item["sample"] in {"ideation.zip", "react-effect-patterns.zip"} else "synthetic"
        sample = _ensure(samples, item["sample"], source_type, "stage28_controlled")
        sample["runtime_findings"].append(item)
        sample["risk_summary"]["stage28_verdict"] = item.get("final_verdict")
        sample["existing_gate_decision"] = _gate_from_stage28(item.get("final_verdict", ""), sample.get("existing_gate_decision", ""))
        sample["evidence_paths"].append("analysis_results/controlled_sinkhole_dynamic/dynamic_evidence.json")
    for key, target in [
        ("stage28_sinkhole", "sinkhole_events"),
        ("stage28_honeypot", "honeypot_events"),
        ("stage28_sessions", "multi_session_events"),
        ("stage28_platform", "platform_surface_events"),
    ]:
        payload = sources.get(key, [])
        if not isinstance(payload, list):
            continue
        for item in payload:
            name = item.get("sample")
            if not name:
                continue
            sample = _ensure(samples, name)
            sample[target].append(item)
            sample["evidence_paths"].append(SOURCE_PATHS[key])


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _highest_from_counts(item: dict[str, Any]) -> str:
    for severity in ("critical", "high", "medium", "low"):
        if int(item.get(severity, 0) or 0) > 0:
            return severity.upper()
    return "NONE"


def _norm_sev(value: str) -> str:
    value = (value or "NONE").upper()
    return "NONE" if value == "NONE" else value


def _gate_from_stage28(verdict: str, current: str) -> str:
    if verdict == "high_risk":
        return "blocked"
    if verdict == "suspicious":
        return "manual_review"
    return current or "allowed"
