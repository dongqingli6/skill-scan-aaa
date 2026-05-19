#!/usr/bin/env bash
set -euo pipefail

# Codex safe regression suite.
# Scope: static-only / synthetic-only.
# Safety: no Docker, no Codex, no real strace, no real samples, no network enabling.
# This entrypoint must not read real HOME secrets or token values.

output_dir="analysis_results/codex_safe_regression_static_only"
summary_json="$output_dir/summary.json"
report_md="$output_dir/report.md"

tests=(
  "code/scripts/test_codex_sandbox_hardening_static.sh"
  "code/scripts/test_codex_egress_policy_static.sh"
  "code/scripts/test_codex_syscall_policy_static.sh"
  "code/scripts/test_codex_syscall_policy_synthetic_logs.sh"
  "code/scripts/test_codex_policy_driven_enforcement_static.sh"
  "code/scripts/test_codex_policy_driven_enforcement_synthetic.sh"
  "code/scripts/test_codex_evidence_schema_static.sh"
  "code/scripts/test_codex_schema_validator_synthetic.sh"
  "code/scripts/test_codex_synthetic_attack_matrix.sh"
  "code/scripts/test_codex_enforced_runner_monitor_wiring_static.sh"
  "code/scripts/test_codex_enforcer_policy_plan_only.sh"
)

mkdir -p "$output_dir"

for script in "${tests[@]}"; do
  [ -f "$script" ]
done

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

entrypoint = Path("code/scripts/run_codex_safe_regression_static_only.sh")
targets = [
    Path("code/scripts/test_codex_sandbox_hardening_static.sh"),
    Path("code/scripts/test_codex_egress_policy_static.sh"),
    Path("code/scripts/test_codex_syscall_policy_static.sh"),
    Path("code/scripts/test_codex_syscall_policy_synthetic_logs.sh"),
    Path("code/scripts/test_codex_policy_driven_enforcement_static.sh"),
    Path("code/scripts/test_codex_policy_driven_enforcement_synthetic.sh"),
    Path("code/scripts/test_codex_evidence_schema_static.sh"),
    Path("code/scripts/test_codex_schema_validator_synthetic.sh"),
    Path("code/scripts/test_codex_synthetic_attack_matrix.sh"),
    Path("code/scripts/test_codex_enforced_runner_monitor_wiring_static.sh"),
    Path("code/scripts/test_codex_enforcer_policy_plan_only.sh"),
]

for path in [entrypoint, *targets]:
    text = path.read_text(encoding="utf-8")
    dangerous = [
        "docker " + "run",
        "docker " + "build",
        "codex " + "exec",
        "strace" + " ",
        "run_" + "skill.sh",
        "run_" + "pipeline.sh",
        "03_" + "download.sh",
        "08_" + "execute.sh",
    ]
    for pattern in dangerous:
        if pattern in text:
            raise AssertionError(f"fail closed: forbidden command pattern {pattern!r} found in {path}")
    if path.suffix == ".py":
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
                raise AssertionError(f"eval is forbidden: {path}")
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        raise AssertionError(f"shell=True is forbidden: {path}")

print("Codex safe regression preflight passed.")
PY

results=()
passed=0
failed=0

for script in "${tests[@]}"; do
  echo "[codex-safe-regression] running $script"
  if bash "$script"; then
    echo "[codex-safe-regression] PASS $script"
    results+=("$script|PASS")
    passed=$((passed + 1))
  else
    echo "[codex-safe-regression] FAIL $script"
    results+=("$script|FAIL")
    failed=$((failed + 1))
  fi
done

total_tests="${#tests[@]}"
if [ "$failed" -eq 0 ]; then
  final_status="PASS"
else
  final_status="FAIL"
fi

python3 - "$summary_json" "$report_md" "$total_tests" "$passed" "$failed" "$final_status" "${results[@]}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
total_tests = int(sys.argv[3])
passed = int(sys.argv[4])
failed = int(sys.argv[5])
final_status = sys.argv[6]
raw_results = sys.argv[7:]

test_results = []
for raw in raw_results:
    name, status = raw.split("|", 1)
    test_results.append({"name": name, "status": status})

summary = {
    "total_tests": total_tests,
    "passed": passed,
    "failed": failed,
    "docker_executed": False,
    "codex_executed": False,
    "strace_executed": False,
    "real_samples_executed": False,
    "network_enabled": False,
    "final_status": final_status,
    "tests": test_results,
}

summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

lines = [
    "# Codex Safe Regression Static-Only Report",
    "",
    "## Test List",
    "",
]
for result in test_results:
    lines.append(f"- {result['status']}: `{result['name']}`")

lines.extend(
    [
        "",
        "## Safety Boundary Confirmation",
        "",
        "- Docker executed: false",
        "- Codex executed: false",
        "- Strace executed: false",
        "- Real samples executed: false",
        "- Network enabled: false",
        "- Real tokens read or passed: false",
        "- Real HOME credential reads: false",
        "",
        "## Final Verdict",
        "",
        f"{final_status}: {passed}/{total_tests} tests passed.",
        "",
    ]
)

report_path.write_text("\n".join(lines), encoding="utf-8")
PY

echo "[codex-safe-regression] wrote $summary_json"
echo "[codex-safe-regression] wrote $report_md"

if [ "$failed" -ne 0 ]; then
  echo "Codex safe regression static-only suite failed."
  exit 1
fi

echo "Codex safe regression static-only suite passed."
