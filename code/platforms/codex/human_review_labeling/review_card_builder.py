from __future__ import annotations

from typing import Any

import kill_chain_mapper
import verdict_policy


def build_review_card(evidence: dict[str, Any]) -> dict[str, Any]:
    labels = infer_taxonomy_labels(evidence)
    verdict = verdict_policy.recommend_verdict(_verdict_input(evidence), labels, evidence.get("source_type", "unknown"))
    phases = kill_chain_mapper.map_labels_to_phases(labels)
    return {
        "sample": evidence["sample_name"],
        "source_type": evidence.get("source_type", "unknown"),
        "static_findings": evidence.get("static_findings", []),
        "agent_findings": evidence.get("agent_findings", []),
        "divergence_findings": evidence.get("divergence_findings", []),
        "runtime_findings": evidence.get("runtime_findings", []),
        "sinkhole_events": evidence.get("sinkhole_events", []),
        "canary_hits": evidence.get("honeypot_events", []),
        "honeypot_touched": any(item.get("honeypot_touched") for item in evidence.get("honeypot_events", [])) or any(item.get("honeypot_touched") for item in evidence.get("runtime_findings", [])),
        "honeypot_exfiltrated": any(item.get("honeypot_exfiltrated") for item in evidence.get("honeypot_events", [])) or any(item.get("honeypot_exfiltrated") for item in evidence.get("runtime_findings", [])),
        "platform_config_touched": bool(evidence.get("platform_surface_events")) or any(item.get("platform_config_touched") for item in evidence.get("runtime_findings", [])),
        "multi_session_triggered": any(item.get("multi_session_triggered") for item in evidence.get("runtime_findings", [])) or len(evidence.get("multi_session_events", [])) > 1,
        "shadow_features": sorted({feature for item in evidence.get("runtime_findings", []) for feature in item.get("shadow_features", [])}),
        "taxonomy_labels": labels,
        "kill_chain_phases": phases,
        "severity": verdict["severity"],
        "confidence": verdict["confidence"],
        "recommended_verdict": verdict["recommended_verdict"],
        "verdict_note": verdict.get("verdict_note", ""),
        "manual_verdict": "",
        "reviewer_notes": "",
        "evidence_paths": sorted(set(evidence.get("evidence_paths", []))),
    }


def infer_taxonomy_labels(evidence: dict[str, Any]) -> list[str]:
    labels: set[str] = set()
    text = str(evidence).lower()
    if evidence.get("existing_gate_decision") == "blocked":
        labels.add("BLOCKED_BY_POLICY")
    if evidence.get("existing_gate_decision") == "manual_review":
        labels.add("MANUAL_REVIEW_REQUIRED")
    if "curl" in text or "network" in text or evidence.get("sinkhole_events"):
        labels.add("NET_ATTEMPT")
    if evidence.get("sinkhole_events"):
        labels.add("SINKHOLE_TOUCH")
    if "x-api-key" in text or "token" in text:
        labels.add("TOKEN_PATTERN")
    if ".env" in text:
        labels.add("ENV_ACCESS")
    if "ssh" in text or "id_rsa" in text:
        labels.add("SSH_KEY_ACCESS")
    if "honeypot_touched': true" in text or any(item.get("honeypot_touched") for item in evidence.get("runtime_findings", [])):
        labels.add("CRED_ACCESS")
    if any(item.get("honeypot_exfiltrated") for item in evidence.get("runtime_findings", [])) or any(item.get("honeypot_exfiltrated") for item in evidence.get("honeypot_events", [])):
        labels.update({"CRED_EXFIL", "NET_EXFIL"})
    if "docker.sock" in text:
        labels.add("DOCKER_SOCK")
    if "privileged" in text:
        labels.add("PRIVILEGED_REQ")
    if "host network" in text or "network host" in text:
        labels.add("HOST_NETWORK")
    if "shell" in text or "bash" in text:
        labels.add("SHELL_EXEC")
    if "install" in text:
        labels.add("INSTALL_CMD")
    if "codex exec" in text:
        labels.add("CODEX_EXEC")
    if "strace" in text:
        labels.add("STRACE_EXEC")
    if evidence.get("platform_surface_events") or any(item.get("platform_config_touched") for item in evidence.get("runtime_findings", [])):
        labels.add("PLATFORM_CONFIG_WRITE")
    if ".codex" in text:
        labels.add("CODEX_HOME_TOUCH")
    if "agents.md" in text:
        labels.add("AGENTS_MD_TOUCH")
    if "mcp" in text:
        labels.add("MCP_CONFIG_TOUCH")
    if "approval_policy" in text:
        labels.add("APPROVAL_POLICY_TOUCH")
    if "prompt_injection" in text or "ignore safety" in text or "ignore system" in text:
        labels.add("PROMPT_INJECTION")
    if "hidden_instruction" in text:
        labels.add("HIDDEN_INSTRUCTION")
    if evidence.get("divergence_findings"):
        labels.add("DOC_BEHAVIOR_DIVERGENCE")
    if any(item.get("shadow_features") for item in evidence.get("runtime_findings", [])):
        labels.add("SHADOW_FEATURE")
    if len(evidence.get("multi_session_events", [])) > 1:
        labels.add("MULTI_SESSION_STATE")
    if "delayed" in evidence.get("sample_name", "").lower():
        labels.add("DELAYED_TRIGGER")
    if not labels or evidence.get("risk_summary", {}).get("stage28_verdict") == "benign_controlled":
        labels.add("BENIGN_CONTROLLED")
    return sorted(labels)


def _verdict_input(evidence: dict[str, Any]) -> dict[str, Any]:
    runtime = evidence.get("runtime_findings", [])
    platform_events = evidence.get("platform_surface_events", [])
    return {
        "severity": evidence.get("risk_summary", {}).get("severity") or evidence.get("risk_summary", {}).get("static_severity") or "NONE",
        "existing_gate_decision": evidence.get("existing_gate_decision", ""),
        "evidence_missing": evidence.get("evidence_missing", False),
        "sample_family": evidence.get("sample_family", ""),
        "honeypot_exfiltrated": any(item.get("honeypot_exfiltrated") for item in runtime) or any(item.get("honeypot_exfiltrated") for item in evidence.get("honeypot_events", [])),
        "platform_config_touched": bool(platform_events) or any(item.get("platform_config_touched") for item in runtime),
        "platform_policy_impact": "high" if platform_events else "",
        "benign_controlled": evidence.get("risk_summary", {}).get("stage28_verdict") == "benign_controlled",
    }
