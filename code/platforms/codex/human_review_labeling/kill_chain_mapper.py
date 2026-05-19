from __future__ import annotations


PHASES = [
    "Reconnaissance",
    "Initial Skill Load",
    "Prompt Injection / Instruction Hijack",
    "Credential Access",
    "Platform Configuration Access",
    "Execution",
    "Persistence",
    "Defense Evasion",
    "Exfiltration",
    "Impact",
    "Policy Blocked",
    "Manual Review",
]


def map_labels_to_phases(labels: list[str]) -> list[str]:
    phases = {"Initial Skill Load"}
    if any(label in labels for label in ("PROMPT_INJECTION", "HIDDEN_INSTRUCTION")):
        phases.add("Prompt Injection / Instruction Hijack")
    if any(label in labels for label in ("CRED_ACCESS", "CRED_EXFIL", "ENV_ACCESS", "SSH_KEY_ACCESS", "TOKEN_PATTERN")):
        phases.add("Credential Access")
    if any(label in labels for label in ("PLATFORM_CONFIG_READ", "PLATFORM_CONFIG_WRITE", "AGENTS_MD_TOUCH", "MCP_CONFIG_TOUCH", "CODEX_HOME_TOUCH", "APPROVAL_POLICY_TOUCH")):
        phases.add("Platform Configuration Access")
    if any(label in labels for label in ("SHELL_EXEC", "SCRIPT_EXEC", "INSTALL_CMD", "CODEX_EXEC", "STRACE_EXEC")):
        phases.add("Execution")
    if any(label in labels for label in ("PLATFORM_CONFIG_WRITE", "PERSISTENCE_ATTEMPT", "MULTI_SESSION_STATE", "DELAYED_TRIGGER")):
        phases.add("Persistence")
    if any(label in labels for label in ("SANDBOX_POLICY_DOWNGRADE", "DOCKER_SOCK", "PRIVILEGED_REQ", "HOST_NETWORK")):
        phases.add("Defense Evasion")
    if any(label in labels for label in ("NET_EXFIL", "CRED_EXFIL", "SINKHOLE_TOUCH")):
        phases.add("Exfiltration")
    if "BLOCKED_BY_POLICY" in labels:
        phases.add("Policy Blocked")
    if "MANUAL_REVIEW_REQUIRED" in labels:
        phases.add("Manual Review")
    if labels == ["BENIGN_CONTROLLED"] or "BENIGN_CONTROLLED" in labels:
        phases.add("Reconnaissance")
    return [phase for phase in PHASES if phase in phases]


def matrix(cards: list[dict]) -> dict[str, list[str]]:
    return {card["sample"]: card["kill_chain_phases"] for card in cards}
