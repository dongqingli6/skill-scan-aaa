from __future__ import annotations


TAXONOMY = {
    "Credential / secret": ["CRED_ACCESS", "CRED_EXFIL", "ENV_ACCESS", "SSH_KEY_ACCESS", "TOKEN_PATTERN"],
    "Network / exfil": ["NET_ATTEMPT", "NET_EXFIL", "SINKHOLE_TOUCH", "UNSAFE_ENDPOINT"],
    "Execution": ["SHELL_EXEC", "INSTALL_CMD", "SCRIPT_EXEC", "CODEX_EXEC", "STRACE_EXEC"],
    "Docker / sandbox escape": ["DOCKER_SOCK", "PRIVILEGED_REQ", "HOST_NETWORK", "SANDBOX_POLICY_DOWNGRADE"],
    "Platform / agent-native": [
        "PLATFORM_CONFIG_READ",
        "PLATFORM_CONFIG_WRITE",
        "AGENTS_MD_TOUCH",
        "MCP_CONFIG_TOUCH",
        "CODEX_HOME_TOUCH",
        "APPROVAL_POLICY_TOUCH",
    ],
    "Prompt injection / shadow feature": ["PROMPT_INJECTION", "HIDDEN_INSTRUCTION", "SHADOW_FEATURE", "DOC_BEHAVIOR_DIVERGENCE"],
    "Multi-session": ["DELAYED_TRIGGER", "MULTI_SESSION_STATE", "PERSISTENCE_ATTEMPT"],
    "General": ["BENIGN_CONTROLLED", "MANUAL_REVIEW_REQUIRED", "BLOCKED_BY_POLICY"],
}


def all_labels() -> list[str]:
    labels: list[str] = []
    for values in TAXONOMY.values():
        labels.extend(values)
    return labels


def taxonomy_json() -> dict[str, list[str]]:
    return TAXONOMY
