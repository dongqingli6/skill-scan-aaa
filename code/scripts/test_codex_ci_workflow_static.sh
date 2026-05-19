#!/usr/bin/env bash
set -euo pipefail

# Static-only CI workflow validation.
# This script reads workflow text only. It must not run Docker, Codex, strace,
# real samples, network-enabled commands, dependency installers, or credentials.

workflow=".github/workflows/codex-safe-regression-static-only.yml"
self="code/scripts/test_codex_ci_workflow_static.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "PASS: $*"
}

require_file() {
  local path="$1"
  [ -f "$path" ] || fail "$path does not exist"
  pass "$path exists"
}

require_contains() {
  local path="$1"
  local pattern="$2"
  local label="$3"
  grep -Fq -- "$pattern" "$path" || fail "$label"
  pass "$label"
}

require_not_contains() {
  local path="$1"
  local pattern="$2"
  local label="$3"
  if grep -Fqi -- "$pattern" "$path"; then
    fail "$label"
  fi
  pass "$label"
}

require_file "$workflow"
require_contains "$workflow" "run_codex_safe_regression_static_only.sh" "workflow calls safe regression entrypoint"

require_not_contains "$workflow" "docker build" "workflow must not contain docker build"
require_not_contains "$workflow" "docker run" "workflow must not contain docker run"
require_not_contains "$workflow" "codex exec " "workflow must not contain codex exec command"
require_not_contains "$workflow" "apt install" "workflow must not contain apt install"
require_not_contains "$workflow" "curl" "workflow must not contain curl"
require_not_contains "$workflow" "wget" "workflow must not contain wget"
require_not_contains "$workflow" "npm install" "workflow must not contain npm install"
require_not_contains "$workflow" "pip install" "workflow must not contain pip install"
require_not_contains "$workflow" '${{ secrets' "workflow must not reference GitHub secrets context"
require_not_contains "$workflow" "docker.sock" "workflow must not mount docker.sock"
require_not_contains "$workflow" "--privileged" "workflow must not use --privileged"
require_not_contains "$workflow" "--network host" "workflow must not use --network host"
require_not_contains "$workflow" "prompt_injection_skill" "workflow must not run prompt_injection_skill"
require_not_contains "$workflow" "script_risk_skill" "workflow must not run script_risk_skill"
require_not_contains "$workflow" "agents_pollution_sample" "workflow must not run agents_pollution_sample"
require_not_contains "$workflow" "run_skill.sh" "workflow must not run samples"
require_not_contains "$workflow" "run_pipeline.sh" "workflow must not run pipeline"
require_not_contains "$workflow" "03_download.sh" "workflow must not run download script"
require_not_contains "$workflow" "08_execute.sh" "workflow must not run execution script"

if grep -Eiq 'run:.*(^|[[:space:]])strace([[:space:]]|$)' "$workflow"; then
  fail "workflow must not run strace"
fi
pass "workflow must not run strace"

word_one="$(printf '\\163\\150\\145\\154\\154\\075\\124\\162\\165\\145')"
word_two="$(printf '\\145\\166\\141\\154')"

if grep -Fq -- "$word_one" "$self"; then
  fail "test script itself contains a forbidden shell flag"
fi
pass "test script itself does not contain the forbidden shell flag"

if grep -Eq "(^|[[:space:];])${word_two}([[:space:];]|$)" "$self"; then
  fail "test script itself contains a forbidden evaluator command"
fi
pass "test script itself does not contain the forbidden evaluator command"

echo "Codex CI workflow static validation passed."
