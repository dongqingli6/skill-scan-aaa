#!/bin/bash
#
# Script 6 draft: Multi-platform agent analysis dispatcher.
# Codex mode is static-only/dry-run and never calls Codex CLI.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CODE_ROOT/.." && pwd)"

PLATFORM="${1:-codex}"
QUEUE_FILE="${2:-$REPO_ROOT/queues/codex_analysis_queue.jsonl}"

case "$PLATFORM" in
    claude_code|codex|both) ;;
    *)
        echo "[ERROR] Unsupported platform: $PLATFORM" >&2
        echo "Usage: $0 [claude_code|codex|both] [queue_file]" >&2
        exit 1
        ;;
esac

run_codex_static_only() {
    local queue="$QUEUE_FILE"
    local out_dir="$REPO_ROOT/analysis_results/codex"
    mkdir -p "$out_dir"

    if [ ! -f "$queue" ]; then
        echo "[ERROR] Codex queue not found: $queue" >&2
        echo "Run code/scripts/05_gen_agent_queue.sh codex <root> first." >&2
        exit 1
    fi

    python3 - "$CODE_ROOT" "$queue" "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

project_root = Path(sys.argv[1])
queue = Path(sys.argv[2])
out_dir = Path(sys.argv[3])
sys.path.insert(0, str(project_root))

from platforms.codex.analyzer_adapter import analyze_codex_record_static_only

count = 0
severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
classification_counts = {}
audit_jsonl = out_dir / "agent_audit_results.jsonl"
with queue.open("r", encoding="utf-8") as handle:
    with audit_jsonl.open("w", encoding="utf-8") as out:
        for line in handle:
            if not line.strip():
                continue
            task = json.loads(line)
            record = analyze_codex_record_static_only(task)
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            severity = record.get("severity", "LOW")
            if severity in severity_counts:
                severity_counts[severity] += 1
            classification = record.get("classification", "unknown")
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
            count += 1

summary = {
    "platform": "codex",
    "mode": "static-only",
    "total": count,
    "by_severity": severity_counts,
    "by_classification": classification_counts,
    "dynamic_execution_enabled": False,
}
(out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {count} Codex static-only audit results to {audit_jsonl}")
PY
}

if [ "$PLATFORM" = "codex" ] || [ "$PLATFORM" = "both" ]; then
    echo "[INFO] Running Codex static-only analysis. Codex CLI execution is disabled."
    run_codex_static_only
fi

if [ "$PLATFORM" = "claude_code" ] || [ "$PLATFORM" = "both" ]; then
    echo "[WARN] Claude Code unified analyzer is not wired here. Existing script remains: code/scripts/06_cc_analyze.sh"
fi

echo "[SUCCESS] Agent analysis step complete."
