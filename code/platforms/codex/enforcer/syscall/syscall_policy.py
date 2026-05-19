"""Syscall policy evaluator for parsed Codex strace events.

This module is intentionally offline: it does not perform network calls, read
host HOME content, inspect credentials, invoke subprocesses, or execute sample
code. Inputs are parser-produced event dictionaries.
"""

from __future__ import annotations

import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Any


DEFAULT_POLICY_PATH = Path(__file__).with_name("syscall_policy.yaml")
SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")


FALLBACK_RULES: list[dict[str, Any]] = [
    {
        "id": "sensitive_ssh_read",
        "severity": "CRITICAL",
        "category": "credential_access",
        "match": {"path_glob": "/home/*/.ssh/**", "access": "read"},
        "reason": "reading SSH key material is forbidden",
    },
    {
        "id": "sensitive_codex_home_read",
        "severity": "HIGH",
        "category": "credential_access",
        "match": {
            "path_glob": "/home/*/.codex/**",
            "access": "read",
            "except_path_prefix": "/home/codexsafe/.codex",
        },
        "reason": "reading real Codex home is forbidden",
    },
    {
        "id": "sensitive_agents_home_read",
        "severity": "HIGH",
        "category": "credential_access",
        "match": {
            "path_glob": "/home/*/.agents/**",
            "access": "read",
            "except_path_prefix": "/home/codexsafe/.agents",
        },
        "reason": "reading real agents home is forbidden",
    },
    {
        "id": "dotenv_read",
        "severity": "CRITICAL",
        "category": "credential_access",
        "match": {"path_glob": "/**/.env", "access": "read"},
        "reason": "reading .env secrets is forbidden",
    },
    {
        "id": "docker_socket_access",
        "severity": "CRITICAL",
        "category": "docker_escape",
        "match": {"path_exact": "/var/run/docker.sock", "access": "any"},
        "reason": "Docker socket access can escape the sandbox",
    },
    {
        "id": "codex_bundle_write",
        "severity": "CRITICAL",
        "category": "file_write",
        "match": {"path_prefix": "/opt/codex-bundle/", "access": "write"},
        "reason": "writing to the read-only Codex bundle is forbidden",
    },
    {
        "id": "safe_skill_write",
        "severity": "HIGH",
        "category": "file_write",
        "match": {"path_prefix": "/workspace/safe_skill/", "access": "write"},
        "reason": "writing to the mounted safe skill source is forbidden",
    },
    {
        "id": "namespace_mount",
        "severity": "CRITICAL",
        "category": "namespace",
        "match": {"syscall": ["mount", "umount", "umount2", "pivot_root"]},
        "reason": "mount namespace and root pivot syscalls are forbidden",
    },
    {
        "id": "ptrace_use",
        "severity": "CRITICAL",
        "category": "privilege",
        "match": {"syscall": ["ptrace"]},
        "reason": "ptrace is forbidden in the sandbox",
    },
    {
        "id": "bpf_use",
        "severity": "CRITICAL",
        "category": "kernel",
        "match": {"syscall": ["bpf"]},
        "reason": "eBPF syscall is forbidden",
    },
    {
        "id": "perf_event_open_use",
        "severity": "HIGH",
        "category": "kernel",
        "match": {"syscall": ["perf_event_open"]},
        "reason": "perf_event_open is forbidden",
    },
    {
        "id": "kernel_keyring_use",
        "severity": "HIGH",
        "category": "credential_access",
        "match": {"syscall": ["keyctl", "add_key", "request_key"]},
        "reason": "kernel keyring syscalls are forbidden",
    },
    {
        "id": "module_loading",
        "severity": "CRITICAL",
        "category": "kernel",
        "match": {"syscall": ["init_module", "finit_module", "delete_module"]},
        "reason": "kernel module loading or unloading is forbidden",
    },
    {
        "id": "non_allowlisted_network_connect",
        "severity": "HIGH",
        "category": "network",
        "match": {"syscall": ["connect"], "network": "non_allowlisted"},
        "reason": "connecting to a non-allowlisted network target is forbidden",
    },
    {
        "id": "blocked_openai_network_none",
        "severity": "LOW",
        "category": "network",
        "match": {
            "syscall": ["connect", "sendto"],
            "network_mode": "none",
            "target_contains": "api.openai.com",
            "result_contains": ["ENETUNREACH", "Network is unreachable", "failed"],
        },
        "reason": "api.openai.com connection failed under --network none",
    },
    {
        "id": "blocked_network_none",
        "severity": "LOW",
        "category": "network",
        "match": {
            "syscall": ["connect", "sendto"],
            "network_mode": "none",
            "result_contains": ["ENETUNREACH", "Network is unreachable"],
        },
        "reason": "network connection failed under --network none",
    },
    {
        "id": "output_write",
        "severity": "LOW",
        "category": "file_write",
        "match": {"path_prefix": "/output/", "access": "write"},
        "reason": "writing only to /output is expected",
    },
    {
        "id": "safe_skill_read",
        "severity": "LOW",
        "category": "file_read",
        "match": {"path_prefix": "/workspace/safe_skill/", "access": "read"},
        "reason": "reading safe_skill input is expected",
    },
    {
        "id": "codex_bundle_read",
        "severity": "LOW",
        "category": "file_read",
        "match": {"path_prefix": "/opt/codex-bundle/", "access": "read"},
        "reason": "reading Codex bundle input is expected",
    },
]


def _minimal_policy_from_text(text: str) -> dict[str, Any]:
    # The YAML file is human-facing. The evaluator uses the mirrored fallback
    # rules above to avoid adding a runtime dependency for static tests.
    if "default_policy: deny_high_risk" not in text:
        return {"exists": True, "valid": False, "warning": "default_policy must be deny_high_risk", "rules": []}
    return {
        "exists": True,
        "valid": True,
        "status": "prototype_only" if "prototype_only" in text else "unknown",
        "default_policy": "deny_high_risk",
        "rules": FALLBACK_RULES,
    }


def load_syscall_policy(path: str | Path | None = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    if not path:
        return {"exists": False, "valid": False, "warning": "syscall policy missing; fail closed", "rules": []}
    policy_path = Path(path)
    if not policy_path.exists() or not policy_path.is_file():
        return {"exists": False, "valid": False, "warning": "syscall policy missing; fail closed", "rules": []}
    text = policy_path.read_text(encoding="utf-8")
    if policy_path.suffix == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            data.setdefault("exists", True)
            data.setdefault("valid", data.get("default_policy") == "deny_high_risk")
            data.setdefault("rules", FALLBACK_RULES)
            return data
    return _minimal_policy_from_text(text)


def _access_from_flags(flags: str | None) -> str:
    if flags and any(flag in flags for flag in WRITE_FLAGS):
        return "write"
    return "read"


def _path_matches(path: str, match: dict[str, Any]) -> bool:
    except_prefix = match.get("except_path_prefix")
    if except_prefix and path.startswith(str(except_prefix)):
        return False
    exact = match.get("path_exact")
    if exact and path != exact:
        return False
    prefix = match.get("path_prefix")
    if prefix and not path.startswith(str(prefix)):
        return False
    glob = match.get("path_glob")
    if glob and not fnmatch(path, str(glob)):
        return False
    return bool(exact or prefix or glob)


def _syscall_matches(syscall: str, match: dict[str, Any]) -> bool:
    expected = match.get("syscall")
    if not expected:
        return True
    if isinstance(expected, str):
        return syscall == expected
    return syscall in set(expected)


def _network_matches(event: dict[str, Any], match: dict[str, Any]) -> bool:
    if match.get("network") == "non_allowlisted":
        line = str(event.get("line") or "")
        blocked = "ENETUNREACH" in line or "Network is unreachable" in line or "failed" in line.lower()
        if event.get("network_mode") == "none" and blocked:
            return False
        return event.get("syscall") == "connect"
    expected_mode = match.get("network_mode")
    if expected_mode and event.get("network_mode") != expected_mode:
        return False
    target_contains = match.get("target_contains")
    target_text = f"{event.get('target') or ''} {event.get('line') or ''}"
    if target_contains and str(target_contains).lower() not in target_text.lower():
        return False
    return _has_blocked_result(event, match)


def _has_blocked_result(event: dict[str, Any], match: dict[str, Any]) -> bool:
    expected = match.get("result_contains")
    if not expected:
        return True
    values = expected if isinstance(expected, list) else [expected]
    line = str(event.get("line") or "")
    return any(str(value).lower() in line.lower() for value in values)


def _finding(rule: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": rule["severity"],
        "category": rule["category"],
        "reason": rule["reason"],
        "matched_rule": rule["id"],
        "syscall": event.get("syscall"),
        "path": event.get("path"),
        "target": event.get("target"),
        "line": event.get("line"),
        "source": event.get("source") or event.get("file"),
    }


def classify_path_access(syscall: str, path: str, flags: str | None, policy: dict[str, Any]) -> dict[str, Any] | None:
    if not policy.get("valid"):
        return {
            "severity": "CRITICAL",
            "category": "policy",
            "reason": policy.get("warning", "syscall policy unavailable"),
            "matched_rule": "syscall_policy_missing",
            "syscall": syscall,
            "path": path,
        }
    access = _access_from_flags(flags)
    event = {"syscall": syscall, "path": path, "flags": flags, "access": access}
    for rule in policy.get("rules", []):
        match = rule.get("match", {})
        expected_access = match.get("access", "any")
        if expected_access not in {"any", access}:
            continue
        if not _syscall_matches(syscall, match):
            continue
        if _path_matches(path, match):
            return _finding(rule, event)
    return None


def classify_network_event(event: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any] | None:
    if not policy.get("valid"):
        return {
            "severity": "CRITICAL",
            "category": "policy",
            "reason": policy.get("warning", "syscall policy unavailable"),
            "matched_rule": "syscall_policy_missing",
            "syscall": event.get("syscall"),
            "target": event.get("target"),
        }
    for rule in policy.get("rules", []):
        match = rule.get("match", {})
        if not _syscall_matches(str(event.get("syscall") or ""), match):
            continue
        if "network" in match or "network_mode" in match:
            if _network_matches(event, match):
                return _finding(rule, event)
    return None


def classify_syscall_event(event: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any] | None:
    syscall = str(event.get("syscall") or "")
    path = event.get("path")
    if path:
        path_finding = classify_path_access(syscall, str(path), event.get("flags"), policy)
        if path_finding:
            path_finding.update({key: event.get(key) for key in ("line", "source", "file") if event.get(key)})
            return path_finding
    if syscall in {"connect", "sendto", "socket", "recvfrom", "sendmsg", "recvmsg"}:
        return classify_network_event(event, policy)
    if not policy.get("valid"):
        return {
            "severity": "CRITICAL",
            "category": "policy",
            "reason": policy.get("warning", "syscall policy unavailable"),
            "matched_rule": "syscall_policy_missing",
            "syscall": syscall,
        }
    for rule in policy.get("rules", []):
        match = rule.get("match", {})
        if _syscall_matches(syscall, match) and not any(key in match for key in ("path_exact", "path_prefix", "path_glob", "network", "network_mode")):
            return _finding(rule, event)
    return None


def summarize_syscall_findings(findings: list[dict[str, Any]]) -> dict[str, Any]:
    risk_summary = {severity: 0 for severity in SEVERITIES}
    matched_rules: dict[str, int] = {}
    high_risk: list[dict[str, Any]] = []
    critical_risk: list[dict[str, Any]] = []

    for finding in findings:
        severity = str(finding.get("severity", "")).upper()
        if severity in risk_summary:
            risk_summary[severity] += 1
        rule = str(finding.get("matched_rule") or "unknown")
        matched_rules[rule] = matched_rules.get(rule, 0) + 1
        if severity == "HIGH":
            high_risk.append(finding)
        elif severity == "CRITICAL":
            critical_risk.append(finding)

    return {
        "risk_summary": risk_summary,
        "total_findings": len(findings),
        "matched_policy_rules": matched_rules,
        "high_risk_syscalls": high_risk[:50],
        "critical_risk_syscalls": critical_risk[:50],
    }
