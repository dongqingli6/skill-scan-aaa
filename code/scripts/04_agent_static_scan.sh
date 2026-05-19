#!/bin/bash
#
# Unified static scan entry point draft.
# Codex mode is implemented. Claude Code and both are TODO and do not call the
# original pipeline.
#

set -euo pipefail

PLATFORM="${1:-}"
ROOT="${2:-}"
OUTPUT_DIR="${3:-}"

if [ -z "$PLATFORM" ] || [ -z "$ROOT" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 codex <root> <output_dir>" >&2
    exit 1
fi

case "$PLATFORM" in
    codex)
        python3 code/agent_skill_scan.py \
          --platform codex \
          --root "$ROOT" \
          --mode static-only \
          --output-dir "$OUTPUT_DIR"
        ;;
    claude_code|both)
        echo "TODO: unified static scan for $PLATFORM is not wired. Existing pipeline is intentionally not called." >&2
        exit 1
        ;;
    *)
        echo "Unsupported platform: $PLATFORM" >&2
        exit 1
        ;;
esac
