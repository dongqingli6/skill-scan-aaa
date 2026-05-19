#!/bin/bash
#
# Script 5 draft: Generate multi-platform agent analysis queues.
# This script is static/dry-run only for Codex. It does not execute samples.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CODE_ROOT/.." && pwd)"

PLATFORM="${1:-both}"
SCAN_ROOT="${2:-code/platforms/codex/examples}"
QUEUE_DIR="$REPO_ROOT/queues"
mkdir -p "$QUEUE_DIR"

case "$PLATFORM" in
    claude_code|codex|both) ;;
    *)
        echo "[ERROR] Unsupported platform: $PLATFORM" >&2
        echo "Usage: $0 [claude_code|codex|both] [scan_root]" >&2
        exit 1
        ;;
esac

generate_codex_queue() {
    local output="$QUEUE_DIR/codex_analysis_queue.jsonl"
    local scan_output="$REPO_ROOT/analysis_results/codex/static_scan_results.json"
    mkdir -p "$(dirname "$scan_output")"
    python3 "$CODE_ROOT/platforms/codex/static_scan.py" \
        --root "$REPO_ROOT/$SCAN_ROOT" \
        --output "$scan_output" >/dev/null

    python3 - "$scan_output" "$output" <<'PY'
import json
import sys
from pathlib import Path

scan_output = Path(sys.argv[1])
output = Path(sys.argv[2])
scan = json.loads(scan_output.read_text(encoding="utf-8"))
tasks = [
    {
        "platform": "codex",
        "mode": "static-only",
        "skill_name": skill["skill_name"],
        "source_path": skill["source_path"],
        "skill_md_path": skill["skill_md_path"],
        "agents_md_path": skill.get("agents_md_path"),
        "openai_yaml_path": skill.get("openai_yaml_path"),
        "scripts_paths": skill.get("scripts_paths", []),
        "risk_hint": skill["classification"],
        "allow_dynamic_execution": False,
    }
    for skill in scan.get("skills", [])
]

output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", encoding="utf-8") as handle:
    for task in tasks:
        handle.write(json.dumps(task, ensure_ascii=False) + "\n")

print(f"Generated {len(tasks)} Codex dry-run tasks: {output}")
PY
}

generate_claude_queue_notice() {
    local output="$QUEUE_DIR/claude_code_analysis_queue.jsonl"
    : > "$output"
    echo "[WARN] Claude Code unified queue is a placeholder. Existing script remains: code/scripts/05_gen_cc_queue.sh"
    echo "[INFO] Created placeholder: $output"
}

if [ "$PLATFORM" = "codex" ] || [ "$PLATFORM" = "both" ]; then
    generate_codex_queue
fi

if [ "$PLATFORM" = "claude_code" ] || [ "$PLATFORM" = "both" ]; then
    generate_claude_queue_notice
fi

echo "[SUCCESS] Agent queue generation complete (dry-run safe)."
