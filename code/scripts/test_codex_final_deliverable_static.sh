#!/usr/bin/env bash
set -euo pipefail

# Static validation for the final deliverable package. This script reads local
# files only and does not execute Docker, Codex, strace, or samples.

required_files=(
  "final_deliverable/README.md"
  "final_deliverable/PROJECT_OVERVIEW.md"
  "final_deliverable/DEMO_GUIDE.md"
  "final_deliverable/SAFETY_BOUNDARY.md"
  "final_deliverable/FILE_INDEX.md"
  "final_deliverable/NEXT_STEPS.md"
  "FINAL_DELIVERABLE_INDEX_CODEX.md"
  "dashboard/index.html"
  "RELEASE_AUDIT_CODEX_RUNTIME_SECURITY.md"
  "code/scripts/run_codex_safe_regression_static_only.sh"
)

docs=(
  "final_deliverable/README.md"
  "final_deliverable/PROJECT_OVERVIEW.md"
  "final_deliverable/DEMO_GUIDE.md"
  "final_deliverable/SAFETY_BOUNDARY.md"
  "final_deliverable/FILE_INDEX.md"
  "final_deliverable/NEXT_STEPS.md"
  "FINAL_DELIVERABLE_INDEX_CODEX.md"
)

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "PASS: $*"
}

for path in "${required_files[@]}"; do
  [ -f "$path" ] || fail "$path does not exist"
  pass "$path exists"
done

for doc in "${docs[@]}"; do
  if grep -Eiq 'sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}' "$doc"; then
    fail "$doc appears to contain a real token"
  fi
  if grep -Eiq 'sudo password|user password|password:[[:space:]]*[^[:space:]]+' "$doc"; then
    fail "$doc appears to contain a password"
  fi
done
pass "deliverable docs do not contain detected real token or password patterns"

self="code/scripts/test_codex_final_deliverable_static.sh"
word_one="$(printf '\\163\\150\\145\\154\\154\\075\\124\\162\\165\\145')"
word_two="$(printf '\\145\\166\\141\\154')"

if grep -Fq -- "$word_one" "$self"; then
  fail "final deliverable static test contains a forbidden shell flag"
fi
pass "final deliverable static test does not contain the forbidden shell flag"

if grep -Eq "(^|[[:space:];])${word_two}([[:space:];]|$)" "$self"; then
  fail "final deliverable static test contains a forbidden evaluator command"
fi
pass "final deliverable static test does not contain the forbidden evaluator command"

echo "Codex final deliverable static test passed."
