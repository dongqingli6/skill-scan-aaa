#!/bin/bash
#
# Generate Codex sandbox run queue in plan-only mode.
# This script never calls codex exec, Docker, or sample scripts.
#

set -euo pipefail

STATIC_SCAN="${1:-}"
OUTPUT_DIR="${2:-}"

if [ -z "$STATIC_SCAN" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <static_scan_results.json> <output_dir>" >&2
    exit 1
fi

python3 - "$STATIC_SCAN" "$OUTPUT_DIR" <<'PY'
import json
import sys
from pathlib import Path

static_scan = Path(sys.argv[1]).resolve()
output_dir = Path(sys.argv[2]).resolve()
code_root = Path.cwd() / "code"
sys.path.insert(0, str(code_root))

from platforms.codex.sandbox.run_plan import build_codex_run_plan
from platforms.codex.sandbox.sandbox_models import CodexRunQueueItem

data = json.loads(static_scan.read_text(encoding="utf-8"))
skills = data.get("skills", [])
allowed_root = Path(data.get("root", ".")).resolve()
output_dir.mkdir(parents=True, exist_ok=True)

queue_path = output_dir / "codex_run_queue.jsonl"
with queue_path.open("w", encoding="utf-8") as queue:
    for skill in skills:
        skill_name = skill.get("skill_name") or Path(skill["source_path"]).name
        skill_path = Path(skill["source_path"]).resolve()
        skill_output = output_dir / skill_name
        result = build_codex_run_plan(
            skill_path=skill_path,
            output_dir=skill_output,
            allow_dynamic_execution=False,
            allowed_root=allowed_root,
        )
        item = CodexRunQueueItem(
            platform="codex",
            skill_name=skill_name,
            skill_path=str(skill_path),
            run_plan_path=result["run_plan_path"],
            preflight_path=result["preflight_path"],
            allow_dynamic_execution=False,
            network_enabled=False,
            fake_home_required=True,
            real_home_allowed=False,
            real_tokens_allowed=False,
        ).to_dict()
        queue.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Wrote Codex run queue: {queue_path}")
PY
