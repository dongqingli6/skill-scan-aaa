#!/usr/bin/env bash
set -euo pipefail

python3 code/scripts/run_codex_human_review_labeling.py \
  --collect-stage-results \
  --include-real-skills \
  --include-synthetic \
  --output analysis_results/human_review_labeling >/tmp/codex_human_review_output_static.json

python3 - <<'PY'
import csv
import json
from pathlib import Path

root = Path("analysis_results/human_review_labeling")
for name in [
    "summary.json",
    "report.md",
    "review_cards.json",
    "manual_review_queue.md",
    "vulnerability_taxonomy.json",
    "kill_chain_matrix.json",
    "final_label_dataset.json",
    "final_label_dataset.csv",
]:
    assert (root / name).exists(), name
assert (root / "review_cards").is_dir()
cards = json.loads((root / "review_cards.json").read_text(encoding="utf-8"))
assert cards
for card in cards:
    assert card["taxonomy_labels"], card["sample"]
    assert card["kill_chain_phases"], card["sample"]
    assert card["recommended_verdict"], card["sample"]
    assert card["manual_verdict"] == ""
report = (root / "report.md").read_text(encoding="utf-8")
for phrase in ["Sample-level Review Summary", "Taxonomy Distribution", "Kill Chain Matrix", "Limitations"]:
    assert phrase in report
rows = list(csv.DictReader((root / "final_label_dataset.csv").open(encoding="utf-8")))
assert len(rows) == len(cards)
print("Codex human review output static test passed.")
PY

echo "Codex human review output static test passed."
