from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EVIDENCE_FILES = (
    "analysis_results/real_skill_batch_static_dashboard/summary.json",
    "analysis_results/real_skill_batch_static_dashboard/report.md",
    "analysis_results/agent_static_analysis/summary.json",
    "analysis_results/agent_static_analysis/report.md",
    "analysis_results/real_skill_dynamic_monitoring_batch/summary.json",
    "analysis_results/real_skill_dynamic_monitoring_batch/report.md",
    "analysis_results/controlled_skill_activation/summary.json",
    "analysis_results/controlled_skill_activation/report.md",
    "analysis_results/runtime_violation_synthetic_live/summary.json",
)


KEYWORD_GROUPS = {
    "network": ("network", "curl", "wget", "http://", "https://", "outbound", "exfiltration", "download", "upload"),
    "credential": ("token", "secret", "api_key", "api key", "ssh", "id_rsa", ".env", "openai_api_key", "anthropic_api_key", "github_token", "real home", "real codex home"),
    "filesystem": ("filesystem", "forbidden path", "read", "write", "workspace", "~/.codex", "~/.agents", ".env"),
    "docker": ("docker.sock", "/var/run/docker.sock", "privileged", "--network host", "docker control"),
    "install": ("npm install", "pip install", "apt install", "install.sh", "setup.sh", "dependency"),
    "execution": ("run_skill.sh", "shell", "bash", " sh ", "eval", "exec", "command", "script"),
    "prompt_injection": ("ignore safety", "ignore system", "system prompt", "developer message", "bypass", "reveal"),
}


def load_behavior_evidence(repo_root: Path, sample_names: list[str]) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    sources = _load_sources(repo_root)
    by_sample = {sample: _empty_sample(sample) for sample in sample_names}

    _apply_static_dashboard(by_sample, sources)
    _apply_agent_summary(by_sample, sources)
    _apply_dynamic_summary(by_sample, sources)
    _apply_activation_summary(by_sample, sources)
    _apply_per_sample_files(repo_root, by_sample)
    _derive_flags_from_findings(by_sample)

    missing = [item["path"] for item in sources.values() if item["missing"]]
    return {
        "sources": list(sources.values()),
        "samples": by_sample,
        "evidence_missing": bool(missing),
        "missing_sources": missing,
    }


def _load_sources(repo_root: Path) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    for rel in EVIDENCE_FILES:
        path = repo_root / rel
        item: dict[str, Any] = {"path": rel, "missing": not path.exists()}
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            item["text"] = text[:200000]
            if path.suffix == ".json":
                try:
                    item["json"] = json.loads(text)
                except json.JSONDecodeError:
                    item["json_error"] = True
        loaded[rel] = item
    return loaded


def _empty_sample(sample: str) -> dict[str, Any]:
    return {
        "archive_name": sample,
        "source_records": [],
        "evidence_flags": {key: False for key in KEYWORD_GROUPS},
        "risk_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
        "deterministic_highest": "none",
        "agent_highest": "none",
        "final_highest": "none",
        "recommended_gate": "unknown",
        "evidence_missing": False,
    }


def _apply_static_dashboard(by_sample: dict[str, dict[str, Any]], sources: dict[str, dict[str, Any]]) -> None:
    data = sources["analysis_results/real_skill_batch_static_dashboard/summary.json"].get("json") or {}
    for sample in data.get("samples", []):
        name = sample.get("archive_name")
        if name in by_sample:
            record = by_sample[name]
            record["source_records"].append({"source": "real_skill_batch_static_dashboard", "record": sample})
            for sev in record["risk_counts"]:
                record["risk_counts"][sev] = max(record["risk_counts"][sev], int(sample.get(sev, 0) or 0))
            if sample.get("has_network_references"):
                record["evidence_flags"]["network"] = True
            if sample.get("has_docker_references"):
                record["evidence_flags"]["docker"] = True
            if sample.get("has_env_file") or sample.get("has_ssh_references"):
                record["evidence_flags"]["credential"] = True
            if sample.get("has_scripts"):
                record["evidence_flags"]["execution"] = True
            for finding in sample.get("high_findings", []):
                _apply_finding_flags(record, finding)
            record["recommended_gate"] = sample.get("category") or record["recommended_gate"]


def _apply_agent_summary(by_sample: dict[str, dict[str, Any]], sources: dict[str, dict[str, Any]]) -> None:
    data = sources["analysis_results/agent_static_analysis/summary.json"].get("json") or {}
    for sample in data.get("results", []):
        name = sample.get("archive_name")
        if name in by_sample:
            record = by_sample[name]
            record["source_records"].append({"source": "agent_static_analysis", "record": sample})
            record["deterministic_highest"] = sample.get("deterministic_highest") or "none"
            record["agent_highest"] = sample.get("agent_highest") or "none"
            record["final_highest"] = sample.get("final_highest") or "none"
            record["recommended_gate"] = sample.get("recommended_gate") or record["recommended_gate"]


def _apply_dynamic_summary(by_sample: dict[str, dict[str, Any]], sources: dict[str, dict[str, Any]]) -> None:
    data = sources["analysis_results/real_skill_dynamic_monitoring_batch/summary.json"].get("json") or {}
    for name, sample in (data.get("per_sample") or {}).items():
        if name in by_sample:
            by_sample[name]["source_records"].append({"source": "real_skill_dynamic_monitoring_batch", "record": sample})
    for sample in data.get("blocked_archives_not_run", []):
        if sample in by_sample:
            by_sample[sample]["source_records"].append({"source": "real_skill_dynamic_monitoring_batch", "record": {"blocked_not_run": True}})


def _apply_activation_summary(by_sample: dict[str, dict[str, Any]], sources: dict[str, dict[str, Any]]) -> None:
    data = sources["analysis_results/controlled_skill_activation/summary.json"].get("json") or {}
    for sample in data.get("plans", []):
        name = sample.get("sample_name")
        if name in by_sample:
            by_sample[name]["source_records"].append({"source": "controlled_skill_activation", "record": sample})


def _apply_per_sample_files(repo_root: Path, by_sample: dict[str, dict[str, Any]]) -> None:
    for sample, record in by_sample.items():
        slug = sample.replace(".zip", "_zip")
        paths = [
            repo_root / "analysis_results" / "agent_static_analysis" / "agent_reports" / f"{slug}_agent_static_report.json",
            repo_root / "analysis_results" / "agent_static_analysis" / "agent_reports" / f"{slug}_agent_static_report.md",
            repo_root / "analysis_results" / "controlled_skill_activation" / "plans" / f"{slug}_activation_plan.json",
            repo_root / "analysis_results" / "controlled_skill_activation" / "plans" / f"{slug}_activation_plan.md",
        ]
        manifest_dir = repo_root / "analysis_results" / "real_skill_intake" / "manifests"
        for manifest in manifest_dir.glob(f"{sample[:-4]}_*.json"):
            paths.append(manifest)
        reports_dir = repo_root / "analysis_results" / "real_skill_intake" / "reports"
        for report in reports_dir.glob(f"{sample[:-4]}_*"):
            if report.is_file():
                paths.append(report)
            elif report.is_dir():
                paths.extend(path for path in report.rglob("*") if path.is_file())
        found = False
        for path in paths:
            if not path.exists():
                continue
            found = True
            text = path.read_text(encoding="utf-8", errors="replace")
            payload: dict[str, Any] = {"path": str(path.relative_to(repo_root)), "text": text[:50000]}
            if path.suffix == ".json":
                try:
                    payload["json"] = json.loads(text)
                except json.JSONDecodeError:
                    payload["json_error"] = True
            record["source_records"].append({"source": "per_sample_file", "record": payload})
        if not found:
            record["evidence_missing"] = True


def _derive_flags_from_findings(by_sample: dict[str, dict[str, Any]]) -> None:
    for record in by_sample.values():
        for source in record["source_records"]:
            payload = source.get("record", {})
            if isinstance(payload, dict) and isinstance(payload.get("json"), dict):
                for finding in payload["json"].get("findings", []):
                    _apply_finding_flags(record, finding)
        if not record["source_records"]:
            record["evidence_missing"] = True


def _apply_finding_flags(record: dict[str, Any], finding: dict[str, Any]) -> None:
    joined = json.dumps(finding, sort_keys=True).lower()
    for group, terms in KEYWORD_GROUPS.items():
        if any(term in joined for term in terms):
            record["evidence_flags"][group] = True
