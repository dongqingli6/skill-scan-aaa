#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import importlib.util
import sys
from pathlib import Path

root = Path("code/platforms/codex/human_review_labeling")
sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("verdict_policy", root / "verdict_policy.py")
policy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(policy)

assert policy.recommend_verdict({"honeypot_exfiltrated": True, "severity": "LOW"}, [], "real")["recommended_verdict"] == "malicious"
assert policy.recommend_verdict({"severity": "LOW"}, ["DOCKER_SOCK"], "real")["recommended_verdict"] == "blocked"
assert policy.recommend_verdict({"platform_config_touched": True, "platform_policy_impact": "high", "severity": "LOW"}, [], "real")["recommended_verdict"] in ("malicious", "blocked")
assert policy.recommend_verdict({"severity": "HIGH"}, [], "real")["recommended_verdict"] in ("manual_review_required", "blocked")
assert policy.recommend_verdict({"benign_controlled": True, "severity": "NONE"}, [], "real")["recommended_verdict"] == "benign"
assert policy.recommend_verdict({"evidence_missing": True}, [], "real")["recommended_verdict"] == "manual_review_required"
synthetic = policy.recommend_verdict({"sample_family": "attack_like", "severity": "CRITICAL"}, [], "synthetic")
assert synthetic["recommended_verdict"] == "blocked"
assert synthetic["verdict_note"] == "attack_like_validation"

spec = importlib.util.spec_from_file_location("review_card_builder", root / "review_card_builder.py")
builder = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(builder)
card = builder.build_review_card({"sample_name": "x", "source_type": "synthetic", "sample_family": "attack_like", "risk_summary": {"severity": "CRITICAL"}, "existing_gate_decision": "blocked", "evidence_paths": []})
assert card["manual_verdict"] == ""
print("Codex human review verdict policy static test passed.")
PY

echo "Codex human review verdict policy static test passed."
