#!/usr/bin/env bash
set -euo pipefail

policy=code/platforms/codex/enforcer/policy.yaml
egress_policy=code/platforms/codex/enforcer/egress/egress_policy.yaml
egress_design=code/platforms/codex/enforcer/egress/EGRESS_PROXY_DESIGN.md
egress_py=code/platforms/codex/enforcer/egress/egress_policy.py
bundle=/home/empty/.nvm/versions/node/v22.22.2
out=analysis_results/codex_runtime_enforcement/egress_policy_static

mkdir -p "$out"

[ -f "$egress_policy" ]
[ -f "$egress_design" ]
[ -f "$egress_py" ]

python3 -m py_compile \
  code/platforms/codex/enforcer/egress/egress_policy.py \
  code/platforms/codex/enforcer/docker_command_builder.py \
  code/platforms/codex/enforcer/enforced_runner.py

python3 code/platforms/codex/enforcer/enforced_runner.py \
  --skill-path code/platforms/codex/examples/safe_skill \
  --policy "$policy" \
  --codex-bundle-ro "$bundle" \
  --output-dir "$out/output" \
  --mode plan-only \
  --egress-policy "$egress_policy" \
  --network-mode none \
  --plan-output "$out/egress_plan.json" >/tmp/codex_egress_policy_plan.out

python3 code/platforms/codex/enforcer/enforced_runner.py \
  --skill-path code/platforms/codex/examples/safe_skill \
  --policy "$policy" \
  --codex-bundle-ro "$bundle" \
  --output-dir "$out/controlled_output" \
  --mode plan-only \
  --egress-policy "$egress_policy" \
  --network-mode controlled \
  --plan-output "$out/controlled_preview_plan.json" >/tmp/codex_egress_controlled_plan.out

python3 - <<'PY'
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("code").resolve()))

from platforms.codex.enforcer.egress.egress_policy import (
    is_domain_allowed,
    load_egress_policy,
    summarize_egress_policy,
    validate_egress_policy,
)

egress_policy_path = Path("code/platforms/codex/enforcer/egress/egress_policy.yaml")
egress_py_path = Path("code/platforms/codex/enforcer/egress/egress_policy.py")
plan_path = Path("analysis_results/codex_runtime_enforcement/egress_policy_static/egress_plan.json")
controlled_plan_path = Path("analysis_results/codex_runtime_enforcement/egress_policy_static/controlled_preview_plan.json")

policy_text = egress_policy_path.read_text(encoding="utf-8")
policy_text_lower = policy_text.lower()
for required in [
    "prototype only",
    "not enabled by default",
    "requires human approval",
]:
    assert required in policy_text_lower, f"egress policy missing {required}"
for required in [
    "default_action: deny",
    "docker_network_mode_default: none",
    "egress_proxy_enabled: false",
    "enabled: false",
    "placeholder_only",
    "api.openai.com",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
]:
    assert required in policy_text, f"egress policy missing {required}"

policy = load_egress_policy(egress_policy_path)
validation = validate_egress_policy(policy)
summary = summarize_egress_policy(policy)
assert validation["default_action"] == "deny", validation
assert validation["effective_policy"] == "deny_all", validation
assert validation["allowlist_enabled"] is False, validation
assert validation["allowed_domains"] == [], validation
assert summary["network_mode"] == "none", summary
assert summary["egress_policy"] == "deny_all", summary
assert summary["egress_proxy_enabled"] is False, summary
assert is_domain_allowed("api.openai.com", policy) is False
assert is_domain_allowed("example.com", policy) is False
assert validate_egress_policy({})["effective_policy"] == "deny_all"
assert is_domain_allowed("api.openai.com", {}) is False

source = egress_py_path.read_text(encoding="utf-8")
for forbidden in [
    "socket",
    "urllib",
    "http.client",
    "requests",
    "subprocess",
    "os.environ",
    "Path.home",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "SSH_AUTH_SOCK",
]:
    assert forbidden not in source, f"egress_policy.py must not use {forbidden}"

for path in [
    egress_py_path,
    Path("code/platforms/codex/enforcer/docker_command_builder.py"),
    Path("code/platforms/codex/enforcer/enforced_runner.py"),
]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "eval":
                raise AssertionError(f"eval is forbidden: {path}")
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True is forbidden: {path}")

plan = json.loads(plan_path.read_text(encoding="utf-8"))
network = plan["docker_command_preview"]["expected_network_policy"]
preview = plan["docker_command_preview"]["command_preview"]
assert network["network_mode"] == "none", network
assert network["docker_network_mode"] == "none", network
assert network["egress_policy"] == "deny_all", network
assert network["egress_proxy_enabled"] is False, network
assert "--network none" in preview, preview
for forbidden in ["--network host", "--privileged", "/var/run/docker.sock", "docker.sock:/"]:
    assert forbidden not in preview, (forbidden, preview)

controlled = json.loads(controlled_plan_path.read_text(encoding="utf-8"))
controlled_network = controlled["docker_command_preview"]["expected_network_policy"]
controlled_preview = controlled["docker_command_preview"]["command_preview"]
assert controlled_network["network_mode"] == "controlled", controlled_network
assert controlled_network["controlled_network_preview_only"] is True, controlled_network
assert controlled_network["docker_network_mode"] == "none", controlled_network
assert controlled_network["egress_proxy_enabled"] is False, controlled_network
assert "--network none" in controlled_preview, controlled_preview
assert "--network host" not in controlled_preview, controlled_preview

script_text = Path("code/scripts/test_codex_egress_policy_static.sh").read_text(encoding="utf-8")
for forbidden in ["docker " + "run", "docker " + "build", "codex " + "exec", "strace" + " "]:
    assert forbidden not in script_text, f"static test must not run {forbidden}"

print("Codex egress policy static test passed.")
PY

echo "Codex egress policy static test passed."
