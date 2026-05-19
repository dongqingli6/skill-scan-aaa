#!/usr/bin/env bash
set -euo pipefail

seccomp=code/platforms/codex/enforcer/seccomp/codex_safe_seccomp.json
apparmor=code/platforms/codex/enforcer/apparmor/codex-safe-skill-profile
policy=code/platforms/codex/enforcer/policy.yaml
bundle=/home/empty/.nvm/versions/node/v22.22.2
out=analysis_results/codex_runtime_enforcement/sandbox_hardening_static

mkdir -p "$out"

[ -f "$seccomp" ]
[ -f "$apparmor" ]

python3 -m py_compile \
  code/platforms/codex/enforcer/docker_command_builder.py \
  code/platforms/codex/enforcer/runtime_executor.py \
  code/platforms/codex/enforcer/enforced_runner.py

python3 code/platforms/codex/enforcer/enforced_runner.py \
  --skill-path code/platforms/codex/examples/safe_skill \
  --policy "$policy" \
  --codex-bundle-ro "$bundle" \
  --output-dir "$out/output" \
  --mode plan-only \
  --seccomp-profile "$seccomp" \
  --apparmor-profile codex-safe-skill-profile \
  --plan-output "$out/hardening_plan.json" >/tmp/codex_sandbox_hardening_plan.out

python3 - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

seccomp_path = Path("code/platforms/codex/enforcer/seccomp/codex_safe_seccomp.json")
apparmor_path = Path("code/platforms/codex/enforcer/apparmor/codex-safe-skill-profile")
plan_path = Path("analysis_results/codex_runtime_enforcement/sandbox_hardening_static/hardening_plan.json")

seccomp = json.loads(seccomp_path.read_text(encoding="utf-8"))
seccomp_text = seccomp_path.read_text(encoding="utf-8")
assert "prototype" in seccomp.get("comment", "").lower(), seccomp.get("comment")
assert seccomp["defaultAction"] == "SCMP_ACT_ERRNO", seccomp["defaultAction"]

required_syscalls = [
    "mount",
    "umount",
    "pivot_root",
    "ptrace",
    "kexec_load",
    "bpf",
    "perf_event_open",
    "clone3",
    "keyctl",
    "add_key",
    "request_key",
    "reboot",
    "swapon",
    "swapoff",
    "init_module",
    "finit_module",
    "delete_module",
]
for syscall in required_syscalls:
    assert syscall in seccomp_text, f"seccomp profile must mention {syscall}"

explicit_denies = {
    name
    for entry in seccomp["syscalls"]
    if entry.get("action") == "SCMP_ACT_ERRNO"
    for name in entry.get("names", [])
}
for syscall in required_syscalls:
    assert syscall in explicit_denies, f"seccomp profile must explicitly deny {syscall}"

apparmor = apparmor_path.read_text(encoding="utf-8")
for required in [
    "/output/** rw",
    "/tmp/** rw",
    "/workspace/safe_skill/** r",
    "/opt/codex-bundle/** r",
    "/home/codexsafe/** r",
    "deny /home/*/.ssh/**",
    "deny /home/*/.codex/**",
    "deny /home/*/.agents/**",
    "deny /**/.env",
    "deny /var/run/docker.sock",
    "deny capability sys_admin",
    "deny capability sys_ptrace",
    "deny capability net_raw",
    "deny network raw",
    "profile codex-safe-skill-profile",
]:
    assert required in apparmor, f"AppArmor profile missing {required}"

plan = json.loads(plan_path.read_text(encoding="utf-8"))
assert plan["mode"] == "plan-only", plan
assert plan["dynamic_execution_performed"] is False, plan
preview = plan["docker_command_preview"]["command_preview"]
for required in [
    "--network none",
    "--read-only",
    "--cap-drop ALL",
    "no-new-privileges",
    "--security-opt seccomp=code/platforms/codex/enforcer/seccomp/codex_safe_seccomp.json",
    "--security-opt apparmor=codex-safe-skill-profile",
    ":/workspace/safe_skill:ro",
    ":/output:rw",
    ":/opt/codex-bundle:ro",
]:
    assert required in preview, (required, preview)
for forbidden in ["--privileged", "--network host", "/var/run/docker.sock", "docker.sock:/"]:
    assert forbidden not in preview, (forbidden, preview)
assert plan["docker_command_preview"]["safety_errors"] == [], plan["docker_command_preview"]["safety_errors"]

hardening = plan["docker_command_preview"]["sandbox_hardening"]
assert hardening["plan_only"] is True, hardening
assert hardening["production_enabled"] is False, hardening
assert hardening["seccomp_profile"] == "code/platforms/codex/enforcer/seccomp/codex_safe_seccomp.json", hardening
assert hardening["apparmor_profile"] == "codex-safe-skill-profile", hardening

for path in [
    Path("code/platforms/codex/enforcer/docker_command_builder.py"),
    Path("code/platforms/codex/enforcer/runtime_executor.py"),
    Path("code/platforms/codex/enforcer/enforced_runner.py"),
]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "eval":
                raise AssertionError(f"eval is forbidden: {path}")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

executor = Path("code/platforms/codex/enforcer/runtime_executor.py").read_text(encoding="utf-8")
command_slice = executor[executor.index("command = [") : executor.index("validate_docker_command(command)")]
assert "seccomp=" not in command_slice, "seccomp must remain plan-only for now"
assert "apparmor=" not in command_slice, "AppArmor must remain plan-only for now"
assert "subprocess.Popen(command" in executor, "runtime execution must use an argument list"
assert "[docker_cmd, \"kill\", container_name]" in executor, "docker kill must use an argument list"

script_text = Path("code/scripts/test_codex_sandbox_hardening_static.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec", "strace" + " "]:
    assert forbidden not in script_text, f"static test must not run {forbidden}"

print("Codex sandbox hardening static test passed.")
PY

echo "Codex sandbox hardening static test passed."
