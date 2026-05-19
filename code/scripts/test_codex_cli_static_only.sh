#!/bin/bash
set -euo pipefail

python3 -m py_compile \
  code/core/models.py \
  code/core/report_writer.py \
  code/core/schema_validation.py \
  code/core/safety_guard.py \
  code/platforms/codex/locator.py \
  code/platforms/codex/rules/codex_rules.py \
  code/platforms/codex/static_scan.py \
  code/platforms/codex/analyzer_adapter.py \
  code/platforms/codex/executor_adapter.py \
  code/agent_skill_scan.py

unset OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN CODEX_HOME SSH_AUTH_SOCK || true

python3 code/agent_skill_scan.py \
  --platform codex \
  --root code/platforms/codex/examples \
  --mode static-only \
  --output-dir analysis_results/codex_cli_test

python3 code/core/schema_validation.py \
  --static analysis_results/codex_cli_test/static_scan_results.json

python3 code/core/schema_validation.py \
  --jsonl analysis_results/codex_cli_test/queues/codex_analysis_queue.jsonl

python3 code/core/schema_validation.py \
  --jsonl analysis_results/codex_cli_test/agent_audit_results.jsonl

python3 code/core/schema_validation.py \
  --summary analysis_results/codex_cli_test/summary.json

test -f analysis_results/codex_cli_test/report.md

echo "Codex CLI static-only integration test passed."
