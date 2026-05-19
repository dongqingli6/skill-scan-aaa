"""Parse existing strace logs into a defensive dynamic evidence report.

This module only reads existing strace output. It does not run strace, Docker,
Codex, or samples.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.enforcer.syscall.syscall_policy import (
        DEFAULT_POLICY_PATH,
        classify_syscall_event,
        load_syscall_policy,
        summarize_syscall_findings,
    )
else:  # pragma: no cover
    from ..enforcer.syscall.syscall_policy import (
        DEFAULT_POLICY_PATH,
        classify_syscall_event,
        load_syscall_policy,
        summarize_syscall_findings,
    )


SYSCALLS = [
    "execve",
    "openat",
    "socket",
    "connect",
    "sendto",
    "recvfrom",
    "unlink",
    "rename",
    "chmod",
    "chown",
    "mkdir",
    "rmdir",
    "clone",
    "mount",
    "umount",
    "umount2",
    "pivot_root",
    "ptrace",
    "bpf",
    "perf_event_open",
    "keyctl",
    "add_key",
    "request_key",
    "init_module",
    "finit_module",
    "delete_module",
]

WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")
REAL_SENSITIVE_PATTERNS = (
    "/.ssh",
    ".env",
    "/root/.codex",
    "/root/.agents",
    "/home/empty/.codex",
    "/home/empty/.agents",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "credential",
    "token",
)
FAKE_CODEX_HOME = "/home/codexsafe/.codex"
EVIDENCE_LIMIT = 200


def natural_key(path: Path) -> list[Any]:
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part for part in parts]


def expand_input(input_value: str | Path) -> list[Path]:
    raw = str(input_value)
    path = Path(raw)

    if any(char in raw for char in "*?["):
        return sorted((Path(p) for p in glob.glob(raw)), key=natural_key)

    if path.is_dir():
        candidates = [path / "strace.log", *path.glob("strace.log.*")]
        return sorted((p for p in candidates if p.is_file()), key=natural_key)

    if path.is_file() and path.name == "strace.log":
        candidates = [path, *path.parent.glob("strace.log.*")]
        return sorted((p for p in candidates if p.is_file()), key=natural_key)

    if path.is_file():
        return [path]

    return []


def syscall_name(line: str) -> str | None:
    match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\(", line)
    return match.group(1) if match else None


def quoted_path(line: str) -> str | None:
    match = re.search(r'"([^"]+)"', line)
    return match.group(1) if match else None


def open_flags(line: str) -> str | None:
    match = re.search(r'"[^"]+"\s*,\s*([^,)]+)', line)
    return match.group(1).strip() if match else None


def exec_command(line: str) -> str | None:
    if "execve(" not in line:
        return None
    return quoted_path(line)


def connect_target(line: str) -> str | None:
    if "connect(" not in line and "sendto(" not in line:
        return None
    inet = re.search(r'sin_addr=inet_addr\("([^"]+)"\).*?sin_port=htons\((\d+)\)', line)
    if inet:
        return f"{inet.group(1)}:{inet.group(2)}"
    family = re.search(r"sa_family=([A-Z0-9_]+)", line)
    if family:
        return family.group(1)
    if "api.openai.com" in line:
        return "api.openai.com"
    return None


def line_event(line: str, file: Path, network_disabled: bool = True) -> dict[str, Any]:
    name = syscall_name(line)
    path = quoted_path(line)
    return {
        "syscall": name,
        "path": path,
        "flags": open_flags(line) if name == "openat" else None,
        "target": connect_target(line),
        "network_mode": "none" if network_disabled else "controlled",
        "line": line,
        "file": str(file),
        "source": str(file),
    }


def is_write_line(name: str | None, line: str) -> bool:
    if name == "openat":
        return any(flag in line for flag in WRITE_FLAGS)
    return name in {"unlink", "rename", "chmod", "chown", "mkdir", "rmdir"}


def is_real_sensitive_line(line: str) -> bool:
    normalized = line.replace("\\", "")
    if FAKE_CODEX_HOME in normalized:
        normalized = normalized.replace(FAKE_CODEX_HOME, "")
    return any(pattern.lower() in normalized.lower() for pattern in REAL_SENSITIVE_PATTERNS)


def add_evidence(bucket: list[dict[str, Any]], item: dict[str, Any]) -> None:
    if len(bucket) < EVIDENCE_LIMIT:
        bucket.append(item)


def finding(severity: str, category: str, path: str | None, line: str, file: Path) -> dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "path": path,
        "file": str(file),
        "line": line,
    }


def classify_line(
    line: str,
    file: Path,
    network_disabled: bool = True,
    syscall_policy: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    policy = syscall_policy or load_syscall_policy(DEFAULT_POLICY_PATH)
    event = line_event(line, file, network_disabled=network_disabled)
    policy_finding = classify_syscall_event(event, policy)
    if policy_finding:
        return {
            "severity": policy_finding["severity"],
            "category": policy_finding["category"],
            "path": policy_finding.get("path") or policy_finding.get("target"),
            "file": str(file),
            "line": line,
            "reason": policy_finding.get("reason"),
            "matched_rule": policy_finding.get("matched_rule"),
            "syscall": policy_finding.get("syscall"),
        }

    path = quoted_path(line)
    lower = line.lower()

    if "permission denied" in lower:
        return finding("LOW", "permission_denied", path, line, file)

    if "failed to connect to websocket" in lower or "failed to lookup address information" in lower:
        return finding("LOW", "network_failure_text", None, line, file)

    return None


def parse_strace_log(
    input_path: str | Path,
    network_disabled: bool = True,
    syscall_policy_path: str | Path | None = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:
    files = expand_input(input_path)
    syscall_policy = load_syscall_policy(syscall_policy_path)
    summary_counts = {name: 0 for name in SYSCALLS}
    evidence: dict[str, list[dict[str, Any]]] = {
        "execve_commands": [],
        "network_syscalls": [],
        "connect_targets": [],
        "openat_paths": [],
        "write_paths": [],
        "blocked_network": [],
        "permission_denied": [],
        "network_failure_text": [],
    }
    findings: list[dict[str, Any]] = []
    total_lines = 0

    for file in files:
        for line_no, line in enumerate(file.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            total_lines += 1
            name = syscall_name(line)
            if name in summary_counts:
                summary_counts[name] += 1

            path = quoted_path(line)
            source = {"file": str(file), "line_number": line_no, "line": line}

            command = exec_command(line)
            if command:
                add_evidence(evidence["execve_commands"], {**source, "command": command})

            if name in {"socket", "connect", "sendto", "recvfrom"}:
                target = connect_target(line)
                add_evidence(evidence["network_syscalls"], {**source, "syscall": name, "target": target})
                if name == "connect" and target:
                    add_evidence(evidence["connect_targets"], {**source, "target": target})

            if name == "openat" and path:
                add_evidence(evidence["openat_paths"], {**source, "path": path})

            if is_write_line(name, line):
                add_evidence(evidence["write_paths"], {**source, "path": path, "syscall": name})

            if "ENETUNREACH" in line or "Network is unreachable" in line:
                add_evidence(evidence["blocked_network"], source)

            if "permission denied" in line.lower():
                add_evidence(evidence["permission_denied"], source)

            if "failed to connect to websocket" in line.lower() or "failed to lookup address information" in line.lower():
                add_evidence(evidence["network_failure_text"], source)

            item = classify_line(line, file, network_disabled=network_disabled, syscall_policy=syscall_policy)
            if item:
                item["line_number"] = line_no
                findings.append(item)

    risk_summary = {severity: 0 for severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
    for item in findings:
        risk_summary[item["severity"]] += 1
    syscall_policy_summary = summarize_syscall_findings(findings)

    return {
        "input": str(input_path),
        "exists": bool(files),
        "input_files": [str(path) for path in files],
        "parsed_file_count": len(files),
        "total_lines": total_lines,
        "summary_counts": summary_counts,
        "evidence": evidence,
        "findings": findings,
        "risk_summary": risk_summary,
        "syscall_policy": {
            "path": str(syscall_policy_path) if syscall_policy_path else None,
            "exists": bool(syscall_policy.get("exists")),
            "valid": bool(syscall_policy.get("valid")),
            "warning": syscall_policy.get("warning"),
        },
        "syscall_policy_summary": syscall_policy_summary,
        "high_risk_syscalls": syscall_policy_summary["high_risk_syscalls"],
        "critical_risk_syscalls": syscall_policy_summary["critical_risk_syscalls"],
        "matched_policy_rules": syscall_policy_summary["matched_policy_rules"],
        "summary": {
            "low": risk_summary["LOW"],
            "medium": risk_summary["MEDIUM"],
            "high": risk_summary["HIGH"],
            "critical": risk_summary["CRITICAL"],
            "total_findings": len(findings),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse existing strace logs")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--network-disabled",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Treat network attempts as blocked evidence when Docker network mode is none.",
    )
    parser.add_argument("--syscall-policy", default=str(DEFAULT_POLICY_PATH))
    args = parser.parse_args()

    result = parse_strace_log(args.input, network_disabled=args.network_disabled, syscall_policy_path=args.syscall_policy)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
