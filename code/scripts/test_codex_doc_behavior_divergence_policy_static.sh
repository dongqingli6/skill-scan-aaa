#!/usr/bin/env bash
set -euo pipefail

# Big Stage 26 policy static test.
# This test does not run Docker, Codex, Claude Code, strace, real skills,
# network commands, uploaded scripts, installers, or real APIs.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

root = Path("code/platforms/codex/doc_behavior_diff")
required = [
    "claim_extractor.py",
    "behavior_evidence_loader.py",
    "divergence_policy.py",
    "divergence_analyzer.py",
    "divergence_report.py",
]
for name in required:
    assert (root / name).exists(), f"{name} missing"

for path in [root / name for name in required]:
    text = path.read_text(encoding="utf-8")
    assert "shell=True" not in text, path
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval call forbidden in {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True forbidden in {path}")

spec = importlib.util.spec_from_file_location("divergence_policy", root / "divergence_policy.py")
policy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(policy)

def claims(**overrides):
    base = {
        "skill_md_present": True,
        "purpose": "Writing advice helper",
        "allowed_operations": ["suggest improvements"],
        "claimed_network_use": {"status": "not_declared", "matched_terms": []},
        "claimed_filesystem_use": {"status": "not_declared", "matched_terms": []},
        "claimed_credential_use": {"status": "not_declared", "matched_terms": []},
        "claimed_install_setup_use": {"status": "not_declared", "matched_terms": []},
        "claimed_execution_behavior": {"status": "not_declared", "matched_terms": []},
        "claimed_docker_use": {"status": "not_declared", "matched_terms": []},
        "claims_local_offline": False,
        "hidden_instruction_indicators": [],
    }
    base.update(overrides)
    return base

def evidence(**flags):
    return {
        "evidence_flags": {
            "network": flags.get("network", False),
            "credential": flags.get("credential", False),
            "filesystem": flags.get("filesystem", False),
            "docker": flags.get("docker", False),
            "install": flags.get("install", False),
            "execution": flags.get("execution", False),
            "prompt_injection": flags.get("prompt_injection", False),
        },
        "deterministic_highest": flags.get("deterministic_highest", "none"),
        "agent_highest": flags.get("agent_highest", "none"),
        "final_highest": flags.get("final_highest", "none"),
        "evidence_missing": flags.get("evidence_missing", False),
    }

def highest(findings):
    return policy.highest_severity([finding["severity"] for finding in findings])

assert highest(policy.classify_divergences(claims(), evidence(credential=True))) == "critical"
assert highest(policy.classify_divergences(claims(), evidence(docker=True))) == "critical"
assert highest(policy.classify_divergences(claims(hidden_instruction_indicators=["ignore system"]), evidence())) in ("critical", "high")
assert highest(policy.classify_divergences(claims(), evidence(network=True))) == "high"
assert highest(policy.classify_divergences(claims(), evidence(install=True))) == "high"
assert highest(policy.classify_divergences(claims(), evidence(execution=True))) == "high"
assert highest(policy.classify_divergences(claims(), evidence(filesystem=True))) == "high"
assert highest(policy.classify_divergences(claims(allowed_operations=[]), evidence(evidence_missing=True))) == "medium"
assert highest(policy.classify_divergences(claims(allowed_operations=[]), evidence())) in ("medium", "low")

summary = policy.summarize_divergence(policy.classify_divergences(claims(), evidence(network=True)), evidence(network=True))
assert summary["decision"] == "blocked"
assert summary["review_queue"] == "human security review"
summary = policy.summarize_divergence(policy.classify_divergences(claims(allowed_operations=[]), evidence(evidence_missing=True)), evidence(evidence_missing=True))
assert summary["decision"] == "manual_review"
assert summary["review_queue"] == "manual review"

print("Codex doc-behavior divergence policy static test passed.")
PY

echo "Codex doc-behavior divergence policy static test passed."
