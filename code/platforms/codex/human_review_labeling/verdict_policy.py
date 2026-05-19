from __future__ import annotations


SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def recommend_verdict(evidence: dict, labels: list[str], source_type: str) -> dict[str, object]:
    severity = evidence.get("severity", "NONE").upper()
    gate = evidence.get("existing_gate_decision", "")
    if evidence.get("evidence_missing"):
        return _result("MEDIUM", "manual_review_required")
    if source_type == "synthetic" and (
        evidence.get("sample_family") == "attack_like"
        or evidence.get("honeypot_exfiltrated")
        or evidence.get("platform_config_touched")
    ):
        return _result(max_severity([severity, "HIGH"]), "blocked", "attack_like_validation")
    if evidence.get("honeypot_exfiltrated"):
        return _result("CRITICAL", "malicious")
    if evidence.get("platform_config_touched") and evidence.get("platform_policy_impact") == "high":
        return _result("CRITICAL", "blocked")
    if any(label in labels for label in ("DOCKER_SOCK", "PRIVILEGED_REQ", "HOST_NETWORK", "CODEX_EXEC", "STRACE_EXEC")):
        return _result("CRITICAL", "blocked")
    if "PROMPT_INJECTION" in labels and any(label in labels for label in ("CRED_ACCESS", "CRED_EXFIL", "ENV_ACCESS", "SSH_KEY_ACCESS")):
        return _result("CRITICAL", "malicious")
    if "SHADOW_FEATURE" in labels and any(label in labels for label in ("NET_ATTEMPT", "SINKHOLE_TOUCH")):
        return _result(max_severity([severity, "HIGH"]), "manual_review_required")
    if severity == "CRITICAL":
        return _result("CRITICAL", "blocked")
    if severity == "HIGH" or gate == "blocked":
        return _result(max_severity([severity, "HIGH"]), "blocked")
    if severity == "MEDIUM" or gate == "manual_review":
        return _result(max_severity([severity, "MEDIUM"]), "manual_review_required")
    if evidence.get("benign_controlled"):
        return _result("LOW", "benign")
    return _result(severity, "manual_review_required" if severity == "LOW" else "benign")


def max_severity(values: list[str]) -> str:
    normalized = [value.upper() if value and value.upper() in SEVERITY_ORDER else "NONE" for value in values]
    return max(normalized, key=lambda value: SEVERITY_ORDER[value], default="NONE")


def _result(severity: str, verdict: str, note: str = "") -> dict[str, object]:
    confidence = {"NONE": 0.25, "LOW": 0.55, "MEDIUM": 0.7, "HIGH": 0.85, "CRITICAL": 0.95}.get(severity, 0.5)
    return {"severity": severity, "recommended_verdict": verdict, "confidence": confidence, "verdict_note": note}
