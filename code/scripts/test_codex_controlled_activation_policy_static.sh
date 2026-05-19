#!/usr/bin/env bash
set -euo pipefail

# Big Stage 25 controlled activation policy static test.
# This test does not run Docker, Codex, Claude Code, strace, real skills,
# network commands, uploaded scripts, or dependency installers.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

path = Path("code/platforms/codex/controlled_activation/activation_policy.py")
assert path.exists(), "activation_policy.py missing"
text = path.read_text(encoding="utf-8")
assert "shell=True" not in text
tree = ast.parse(text, filename=str(path))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval call forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True forbidden")

spec = importlib.util.spec_from_file_location("activation_policy", path)
policy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(policy)

assert policy.ALLOWED_SAMPLE_NAMES == ("ideation.zip", "react-effect-patterns.zip")
assert "implementation-guide.zip" in policy.FORBIDDEN_SAMPLE_NAMES
assert "logging-best-practices.zip" in policy.FORBIDDEN_SAMPLE_NAMES
assert "val-town-cli.zip" in policy.FORBIDDEN_SAMPLE_NAMES

zero = {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
high = {"critical": 0, "high": 1, "medium": 0, "low": 0, "informational": 0}
medium = {"critical": 0, "high": 0, "medium": 1, "low": 0, "informational": 0}
candidates = [{"command": "metadata"}]
allowed = policy.evaluate_activation_policy("ideation.zip", zero, zero, candidates, stage21_passed=True, stage23_passed=True)
assert allowed["decision"] == "requires_human_confirmation", allowed
confirmed = policy.evaluate_activation_policy("ideation.zip", zero, zero, candidates, stage21_passed=True, stage23_passed=True, human_confirmed=True)
assert confirmed["decision"] == "allowed", confirmed
assert policy.evaluate_activation_policy("implementation-guide.zip", zero, zero, candidates, stage21_passed=True, stage23_passed=True)["decision"] == "denied"
assert policy.evaluate_activation_policy("logging-best-practices.zip", zero, zero, candidates, stage21_passed=True, stage23_passed=True)["decision"] == "denied"
assert policy.evaluate_activation_policy("val-town-cli.zip", zero, zero, candidates, stage21_passed=True, stage23_passed=True)["decision"] == "denied"
assert policy.evaluate_activation_policy("ideation.zip", high, zero, candidates, stage21_passed=True, stage23_passed=True)["decision"] == "denied"
assert policy.evaluate_activation_policy("ideation.zip", medium, zero, candidates, stage21_passed=True, stage23_passed=True)["decision"] == "denied"
assert policy.evaluate_activation_policy("ideation.zip", zero, high, candidates, stage21_passed=True, stage23_passed=True)["decision"] == "denied"
assert policy.evaluate_activation_policy("ideation.zip", zero, zero, [], stage21_passed=True, stage23_passed=True)["decision"] == "skip"

for command in ["help", "--help", "version", "--version", "dry-run", "--dry-run", "metadata", "inspect", "list"]:
    assert policy.evaluate_entrypoint_command(command)["allowed"] is True, command
for command in [
    "curl",
    "wget",
    "npm install",
    "pip install",
    "apt install",
    "bash",
    "sh",
    "eval",
    "exec",
    "docker",
    "/var/run/docker.sock",
    "~/.codex",
    "~/.agents",
    ".env",
    "id_rsa",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
]:
    assert policy.evaluate_entrypoint_command(command)["allowed"] is False, command

unsafe = policy.evaluate_activation_policy("ideation.zip", zero, zero, [{"command": "curl"}], stage21_passed=True, stage23_passed=True)
assert unsafe["decision"] == "denied", unsafe
assert unsafe["denied_entrypoints"], unsafe

print("Codex controlled activation policy static test passed.")
PY

echo "Codex controlled activation policy static test passed."
