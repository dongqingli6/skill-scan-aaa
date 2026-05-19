#!/usr/bin/env bash
set -euo pipefail

# Big Stage 27 metrics static test.

python3 - <<'PY'
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

path = Path("code/platforms/codex/scaled_validation/metrics.py")
assert path.exists(), "metrics.py missing"
spec = importlib.util.spec_from_file_location("metrics", path)
metrics = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(metrics)

results = [
    {"sample_type": "synthetic", "sample_family": "attack_like", "final_severity": "high", "gate": "blocked", "divergence": "high"},
    {"sample_type": "synthetic", "sample_family": "attack_like", "final_severity": "none", "gate": "allowed", "divergence": "none"},
    {"sample_type": "synthetic", "sample_family": "benign", "final_severity": "none", "gate": "allowed", "divergence": "none"},
    {"sample_type": "synthetic", "sample_family": "benign", "final_severity": "high", "gate": "blocked", "divergence": "high"},
    {"sample_type": "synthetic", "sample_family": "suspicious", "final_severity": "medium", "gate": "manual_review", "divergence": "medium"},
]
computed = metrics.compute_metrics(results)
assert computed["true_positive"] == 1
assert computed["true_negative"] == 1
assert computed["false_positive"] == 1
assert computed["false_negative"] == 1
assert computed["suspicious_manual_review_count"] == 1
assert computed["precision"] == 0.5
assert computed["recall"] == 0.5
assert computed["f1"] == 0.5
matrix = metrics.confusion_matrix(computed)
assert matrix["false_negative"] == 1

out = Path("analysis_results/scaled_validation")
out.mkdir(parents=True, exist_ok=True)
(out / "confusion_matrix.json").write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
assert (out / "confusion_matrix.json").exists()

print("Codex scaled validation metrics static test passed.")
PY

echo "Codex scaled validation metrics static test passed."
