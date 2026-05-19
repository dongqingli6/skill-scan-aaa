from __future__ import annotations

from typing import Any


SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def classify_divergences(claims: dict[str, Any], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    flags = evidence.get("evidence_flags", {})

    if _claim_denies_or_omits(claims, "claimed_credential_use") and flags.get("credential"):
        findings.append(_finding("critical", "credential_mismatch", "SKILL.md does not declare credential use but evidence references tokens, SSH, .env, real HOME, or Codex home."))
    if _claim_denies_or_omits(claims, "claimed_docker_use") and flags.get("docker"):
        findings.append(_finding("critical", "docker_mismatch", "SKILL.md does not declare Docker control but evidence references docker.sock, privileged, or host Docker controls."))
    if (claims.get("claims_local_offline") or _claim_denies_or_omits(claims, "claimed_network_use")) and flags.get("network"):
        severity = "critical" if claims.get("claims_local_offline") and flags.get("credential") else "high"
        findings.append(_finding(severity, "network_mismatch", "SKILL.md does not disclose network use consistently with evidence."))
    if claims.get("hidden_instruction_indicators"):
        findings.append(_finding("critical", "hidden_prompt_injection", "SKILL.md contains hidden instruction or prompt-injection indicators."))

    if _claim_denies_or_omits(claims, "claimed_install_setup_use") and flags.get("install"):
        findings.append(_finding("high", "undisclosed_install", "SKILL.md does not declare installation/setup use but evidence references package installers or setup entrypoints."))
    if _claim_denies_or_omits(claims, "claimed_execution_behavior") and flags.get("execution"):
        findings.append(_finding("high", "undisclosed_execution", "SKILL.md does not declare command/script execution but evidence references shell, eval, exec, or scripts."))
    if _claim_denies_or_omits(claims, "claimed_filesystem_use") and flags.get("filesystem"):
        findings.append(_finding("high", "undisclosed_filesystem", "SKILL.md does not declare filesystem access but evidence references sensitive or broad file access."))

    if _looks_like_writing_advice(claims) and any(flags.get(key) for key in ("network", "execution", "filesystem")):
        findings.append(_finding("high", "under_disclosed_risky_behavior", "SKILL.md presents writing/advice behavior while evidence shows possible command, file, or network behavior."))

    if evidence.get("deterministic_highest") != evidence.get("agent_highest") and evidence.get("agent_highest") not in ("", None):
        findings.append(_finding("medium", "scanner_agent_disagreement", "Agent static analysis and deterministic scanner differ; human review required."))
    if evidence.get("evidence_missing"):
        findings.append(_finding("medium", "evidence_missing", "One or more expected evidence sources are missing; do not treat as automatic pass."))
    if _claims_are_ambiguous(claims) and any(flags.get(key) for key in ("filesystem", "install")):
        findings.append(_finding("medium", "ambiguous_docs", "SKILL.md is ambiguous while evidence shows broader file or environment behavior."))

    if not findings and _claims_are_ambiguous(claims):
        findings.append(_finding("low", "incomplete_documentation", "SKILL.md is incomplete or entrypoints are unclear, with no obvious dangerous evidence."))

    return _dedupe_findings(findings)


def summarize_divergence(findings: list[dict[str, Any]], evidence: dict[str, Any]) -> dict[str, Any]:
    highest = highest_severity([finding["severity"] for finding in findings])
    deterministic = evidence.get("deterministic_highest", "none") or "none"
    agent = evidence.get("agent_highest", "none") or "none"
    final = highest_severity([highest, deterministic, agent, evidence.get("final_highest", "none") or "none"])
    if highest in ("critical", "high"):
        decision = "blocked"
        queue = "human security review"
    elif highest == "medium":
        decision = "manual_review"
        queue = "manual review"
    elif highest == "low":
        decision = "note"
        queue = "note"
    else:
        decision = "consistent"
        queue = "none"
    return {
        "divergence_highest": highest,
        "final_risk": final,
        "decision": decision,
        "review_queue": queue,
        "deterministic_risk_preserved": True,
        "agent_risk_can_not_lower_deterministic": True,
    }


def highest_severity(values: list[str]) -> str:
    normalized = [value if value in SEVERITY_ORDER else "none" for value in values]
    return max(normalized, key=lambda value: SEVERITY_ORDER[value], default="none")


def _claim_denies_or_omits(claims: dict[str, Any], key: str) -> bool:
    status = (claims.get(key) or {}).get("status")
    return status in (None, "not_declared", "denied")


def _claims_are_ambiguous(claims: dict[str, Any]) -> bool:
    if not claims.get("skill_md_present"):
        return True
    declared = 0
    for key in (
        "claimed_network_use",
        "claimed_filesystem_use",
        "claimed_credential_use",
        "claimed_install_setup_use",
        "claimed_execution_behavior",
        "claimed_docker_use",
    ):
        if (claims.get(key) or {}).get("status") == "declared":
            declared += 1
    return declared <= 1 and len(claims.get("allowed_operations") or []) <= 2


def _looks_like_writing_advice(claims: dict[str, Any]) -> bool:
    text = " ".join([claims.get("purpose", ""), " ".join(claims.get("allowed_operations") or [])]).lower()
    return any(term in text for term in ("writing", "guide", "advice", "suggest", "ideation", "pattern", "documentation"))


def _finding(severity: str, category: str, reason: str) -> dict[str, Any]:
    return {"severity": severity, "category": category, "reason": reason}


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for finding in findings:
        key = (finding["severity"], finding["category"])
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result
