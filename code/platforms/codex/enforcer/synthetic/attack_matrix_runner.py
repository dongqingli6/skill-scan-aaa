"""Run the Codex synthetic attack matrix through syscall policy classification.

This runner generates only synthetic strace-formatted text. It does not run
Docker, Codex, real strace, or samples.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from platforms.codex.enforcer.syscall.syscall_policy import (
        DEFAULT_POLICY_PATH,
        classify_syscall_event,
        load_syscall_policy,
    )
else:  # pragma: no cover
    from ..syscall.syscall_policy import DEFAULT_POLICY_PATH, classify_syscall_event, load_syscall_policy


DEFAULT_MATRIX = Path(__file__).with_name("attack_matrix.yaml")
DEFAULT_OUTPUT_DIR = Path("analysis_results/codex_synthetic_attack_matrix")


def load_attack_matrix(path: str | Path = DEFAULT_MATRIX) -> dict[str, Any]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    cases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in lines:
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current:
                cases.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = value.strip()
    if current:
        cases.append(current)
    return {"cases": cases}


def generate_synthetic_strace_log(case: dict[str, Any]) -> str:
    return str(case["line"])


def _syscall_name(line: str) -> str | None:
    match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\(", line)
    return match.group(1) if match else None


def _quoted_path(line: str) -> str | None:
    match = re.search(r'"([^"]+)"', line)
    return match.group(1) if match else None


def _open_flags(line: str) -> str | None:
    match = re.search(r'"[^"]+"\s*,\s*([^,)]+)', line)
    return match.group(1).strip() if match else None


def _connect_target(line: str) -> str | None:
    if "api.openai.com" in line:
        return "api.openai.com"
    inet = re.search(r'inet_addr\("([^"]+)"\).*?htons\((\d+)\)', line)
    return f"{inet.group(1)}:{inet.group(2)}" if inet else None


def run_policy_classification(case: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    line = generate_synthetic_strace_log(case)
    syscall = _syscall_name(line)
    event = {
        "syscall": syscall,
        "path": _quoted_path(line),
        "flags": _open_flags(line) if syscall == "openat" else None,
        "target": _connect_target(line),
        "network_mode": "none",
        "line": line,
        "source": f"synthetic:{case['id']}",
    }
    finding = classify_syscall_event(event, policy or load_syscall_policy(DEFAULT_POLICY_PATH))
    action = "record_only"
    if finding and finding.get("severity") in {"HIGH", "CRITICAL"}:
        action = "kill_container"
    elif case.get("expected_action") == "allow":
        action = "allow"
    return {
        "case_id": case["id"],
        "synthetic_line": line,
        "finding": finding,
        "actual_severity": finding.get("severity") if finding else "allowed",
        "actual_action": action,
        "matched_rule": finding.get("matched_rule") if finding else None,
    }


def compare_expected_result(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    expected_severity = case.get("expected_severity")
    actual_severity = result.get("actual_severity")
    if expected_severity == "HIGH_OR_CRITICAL":
        severity_ok = actual_severity in {"HIGH", "CRITICAL"}
    elif expected_severity == "LOW":
        severity_ok = actual_severity in {"LOW", "allowed"}
    else:
        severity_ok = actual_severity == expected_severity

    expected_action = case.get("expected_action")
    actual_action = result.get("actual_action")
    if expected_action == "allow":
        action_ok = actual_action in {"allow", "record_only"}
    else:
        action_ok = actual_action == expected_action

    return {
        **result,
        "expected_severity": expected_severity,
        "expected_action": expected_action,
        "severity_ok": severity_ok,
        "action_ok": action_ok,
        "passed": severity_ok and action_ok,
    }


def _write_markdown(results: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "# Codex Synthetic Attack Matrix",
        "",
        "| case | expected severity | actual severity | expected action | actual action | matched rule | passed |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(
            "| {case_id} | {expected_severity} | {actual_severity} | {expected_action} | {actual_action} | {matched_rule} | {passed} |".format(
                **item
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_matrix_result(output_dir: str | Path = DEFAULT_OUTPUT_DIR, matrix_path: str | Path = DEFAULT_MATRIX) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    policy = load_syscall_policy(DEFAULT_POLICY_PATH)
    matrix = load_attack_matrix(matrix_path)
    results = [compare_expected_result(case, run_policy_classification(case, policy)) for case in matrix["cases"]]
    report = {
        "matrix_path": str(matrix_path),
        "policy_path": str(DEFAULT_POLICY_PATH),
        "total_cases": len(results),
        "passed_cases": sum(1 for item in results if item["passed"]),
        "failed_cases": sum(1 for item in results if not item["passed"]),
        "all_passed": all(item["passed"] for item in results),
        "cases": results,
        "safety_boundaries": {
            "docker_run": False,
            "codex_run": False,
            "real_strace_run": False,
            "samples_run": False,
            "network_enabled": False
        }
    }
    json_path = out / "matrix_result.json"
    md_path = out / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_markdown(results, md_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Codex synthetic attack matrix")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = write_matrix_result(args.output_dir, args.matrix)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
