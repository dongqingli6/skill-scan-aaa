from __future__ import annotations

from typing import Any


REQUIRED_EVENT_FIELDS = (
    "event_id",
    "timestamp",
    "sample_name",
    "container_name",
    "event_type",
    "observed_action",
    "target",
    "source",
    "dry_run",
    "synthetic",
    "evidence",
)

CRITICAL_RULES = {
    "docker_socket_access": ("container_escape_surface", "docker.sock access is forbidden"),
    "privileged_container_requested": ("container_escape_surface", "privileged containers are forbidden"),
    "host_network_requested": ("network_isolation", "host network mode is forbidden"),
    "real_token_exposure": ("secret_exposure", "real token exposure is forbidden"),
    "ssh_key_read": ("secret_exposure", "SSH key reads are forbidden"),
    "real_codex_home_read": ("host_home_exposure", "real Codex home reads are forbidden"),
    "real_agents_home_read": ("host_home_exposure", "real agents home reads are forbidden"),
}

HIGH_RULES = {
    "outbound_network_attempt": ("network_egress", "outbound network attempts are forbidden"),
    "forbidden_path_read": ("host_filesystem", "forbidden host path reads are blocked"),
    "env_file_read": ("secret_exposure", ".env file reads are forbidden"),
    "uploaded_script_execution_attempt": ("uploaded_script", "uploaded script execution is forbidden"),
    "install_command_attempt": ("installer", "install commands are forbidden"),
    "docker_pull_attempt": ("image_policy", "Docker pulls are forbidden"),
    "codex_exec_attempt": ("codex_execution", "Codex execution is forbidden"),
    "strace_attempt": ("trace_execution", "strace is forbidden by default"),
}

MEDIUM_RULES = {
    "suspicious_shell_pattern": ("shell_pattern", "suspicious shell pattern observed"),
    "broad_filesystem_scan": ("filesystem_scan", "broad filesystem scan observed"),
    "unexpected_write_outside_output": ("filesystem_write", "write outside output directory observed"),
}

LOW_RULES = {
    "blocked_network_attempt_under_network_none": ("network_egress", "network attempt was blocked under network none"),
    "benign_denied_operation": ("benign_denial", "benign denied operation recorded"),
}

SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def validate_runtime_violation_event(event: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
    return {
        "valid": not missing,
        "missing_fields": missing,
        "synthetic": event.get("synthetic") is True,
        "dry_run": event.get("dry_run") is True,
    }


def classify_runtime_event(event: dict[str, Any]) -> dict[str, Any]:
    validation = validate_runtime_violation_event(event)
    event_type = str(event.get("event_type", "unknown"))
    if event_type in CRITICAL_RULES:
        category, reason = CRITICAL_RULES[event_type]
        return _finding(event, "CRITICAL", category, event_type, "kill_container", reason, validation)
    if event_type in HIGH_RULES:
        category, reason = HIGH_RULES[event_type]
        return _finding(event, "HIGH", category, event_type, "fail_closed", reason, validation)
    if event_type in MEDIUM_RULES:
        category, reason = MEDIUM_RULES[event_type]
        return _finding(event, "MEDIUM", category, event_type, "fail_closed", reason, validation)
    if event_type in LOW_RULES:
        category, reason = LOW_RULES[event_type]
        return _finding(event, "LOW", category, event_type, "record_only", reason, validation)
    return _finding(event, "LOW", "unknown", "unknown_runtime_event", "record_only", "unknown synthetic event recorded", validation)


def decide_runtime_response(findings: list[dict[str, Any]]) -> dict[str, Any]:
    if not findings:
        return {
            "runtime_response": "allow",
            "action": "allow",
            "reason": "no runtime violation findings",
            "highest_severity": "NONE",
        }
    highest = max(findings, key=lambda item: SEVERITY_ORDER.get(str(item.get("severity")), 0))
    severity = str(highest.get("severity"))
    if severity == "CRITICAL":
        action = "kill_container"
    elif severity == "HIGH":
        action = "fail_closed"
    elif severity == "MEDIUM":
        action = "fail_closed"
    else:
        action = "record_only"
    return {
        "runtime_response": action,
        "action": action,
        "reason": f"{severity} runtime finding response",
        "highest_severity": severity,
    }


def _finding(
    event: dict[str, Any],
    severity: str,
    category: str,
    matched_rule: str,
    action: str,
    reason: str,
    validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "sample_name": event.get("sample_name"),
        "container_name": event.get("container_name"),
        "event_type": event.get("event_type"),
        "severity": severity,
        "category": category,
        "matched_rule": matched_rule,
        "action": action,
        "reason": reason,
        "target": event.get("target"),
        "synthetic": event.get("synthetic") is True,
        "dry_run": event.get("dry_run") is True,
        "event_valid": validation["valid"],
        "missing_fields": validation["missing_fields"],
    }
