"""Plan-only egress policy helpers for Codex runtime sandbox design.

This module does not perform network calls and does not inspect host
credentials or real HOME content. It only loads and summarizes a deny-by-default
policy document for static validation and preview output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DENY_SUMMARY = {
    "default_action": "deny",
    "enabled": False,
    "egress_proxy_enabled": False,
    "allowlist_enabled": False,
    "allowed_domains": [],
    "effective_policy": "deny_all",
}


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    return value


def _load_minimal_yaml(text: str) -> dict[str, Any]:
    """Parse the limited YAML shape used by egress_policy.yaml.

    The project avoids adding parser dependencies for this static-only helper.
    The parser intentionally supports only simple top-level scalars and the
    allowlist.domains list of domain entries used by the prototype policy.
    """

    policy: dict[str, Any] = {}
    domains: list[dict[str, Any]] = []
    in_domains = False
    current_domain: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if indent == 0 and ":" in stripped:
            key, value = stripped.split(":", 1)
            if value.strip():
                policy[key] = _parse_scalar(value.strip())
            else:
                policy[key] = {}
            in_domains = False
            current_domain = None
            continue

        if stripped == "domains:":
            in_domains = True
            continue

        if in_domains and stripped.startswith("- "):
            if current_domain:
                domains.append(current_domain)
            current_domain = {}
            item = stripped[2:]
            if ":" in item:
                key, value = item.split(":", 1)
                current_domain[key.strip()] = _parse_scalar(value.strip())
            continue

        if in_domains and current_domain is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current_domain[key.strip()] = _parse_scalar(value.strip())

    if current_domain:
        domains.append(current_domain)
    allowlist = policy.setdefault("allowlist", {})
    if isinstance(allowlist, dict):
        allowlist["domains"] = domains
    return policy


def load_egress_policy(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    policy_path = Path(path)
    if not policy_path.exists() or not policy_path.is_file():
        return {}
    text = policy_path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _load_minimal_yaml(text)
    return parsed if isinstance(parsed, dict) else {}


def validate_egress_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    if not policy:
        return {**DENY_SUMMARY, "valid": True, "reason": "policy missing; deny all"}

    allowlist = policy.get("allowlist") if isinstance(policy.get("allowlist"), dict) else {}
    domains = allowlist.get("domains") if isinstance(allowlist, dict) else []
    enabled_domains = [
        item.get("domain")
        for item in domains
        if isinstance(item, dict) and item.get("enabled") is True and item.get("domain")
    ]
    allowlist_enabled = bool(policy.get("enabled") is True and allowlist.get("enabled") is True and enabled_domains)
    default_action = str(policy.get("default_action", "deny")).lower()
    egress_proxy_enabled = bool(policy.get("egress_proxy_enabled") is True and allowlist_enabled)

    effective_policy = "allowlist" if default_action == "deny" and egress_proxy_enabled else "deny_all"
    return {
        "valid": default_action == "deny",
        "reason": "deny-by-default policy" if default_action == "deny" else "default_action must be deny",
        "default_action": default_action,
        "enabled": bool(policy.get("enabled") is True),
        "egress_proxy_enabled": egress_proxy_enabled,
        "allowlist_enabled": allowlist_enabled,
        "allowed_domains": sorted(enabled_domains) if allowlist_enabled else [],
        "effective_policy": effective_policy,
    }


def is_domain_allowed(domain: str, policy: dict[str, Any] | None) -> bool:
    if not domain or not policy:
        return False
    summary = validate_egress_policy(policy)
    if summary["effective_policy"] != "allowlist":
        return False
    normalized = domain.strip().lower().rstrip(".")
    return normalized in {item.lower() for item in summary["allowed_domains"]}


def summarize_egress_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    summary = validate_egress_policy(policy)
    return {
        "network_mode": "none",
        "egress_policy": summary["effective_policy"],
        "egress_proxy_enabled": summary["egress_proxy_enabled"],
        "allowed_domains": summary["allowed_domains"],
        "human_approval_required": bool(policy and policy.get("human_approval_required") is True),
        "prototype_only": bool(policy and str(policy.get("status", "")).lower() == "prototype_only"),
    }
