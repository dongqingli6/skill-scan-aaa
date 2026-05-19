from __future__ import annotations


MONITORED_ITEMS = (
    "AGENTS.md",
    ".codex/",
    "openai.yaml",
    ".mcp.json",
    "mcp.json",
    "hooks/",
    "settings.json",
    "approval_policy",
    "sandbox_mode",
    "network_access",
)


def classify_platform_touch(path_or_text: str, operation: str) -> dict[str, object]:
    matched = [item for item in MONITORED_ITEMS if item.lower() in path_or_text.lower()]
    if not matched:
        return {"platform_config_touched": False, "severity": "none", "matched_items": []}
    severity = "high" if operation in {"write", "modify", "rename", "delete"} else "medium"
    if any(item in {"approval_policy", "sandbox_mode", "network_access"} for item in matched):
        severity = "high"
    return {"platform_config_touched": True, "severity": severity, "matched_items": matched}
