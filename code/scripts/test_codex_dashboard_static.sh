#!/usr/bin/env bash
set -euo pipefail

# Static validation for the offline dashboard. This test reads local files only.

generator="code/scripts/generate_codex_runtime_security_dashboard.py"
index="dashboard/index.html"
data="dashboard/dashboard_data.json"
style="dashboard/style.css"
readme="dashboard/README.md"
self="code/scripts/test_codex_dashboard_static.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "PASS: $*"
}

for path in "$generator" "$index" "$data" "$style" "$readme"; do
  [ -f "$path" ] || fail "$path does not exist"
  pass "$path exists"
done

if grep -Eiq 'https?://' "$index"; then
  fail "index.html must not reference http or https resources"
fi
pass "index.html does not reference http or https resources"

if grep -Eiq 'cdn|unpkg|jsdelivr|googleapis|cloudflare' "$index"; then
  fail "index.html must not reference external CDN resources"
fi
pass "index.html does not reference external CDN resources"

python3 -m json.tool "$data" >/tmp/codex_dashboard_data_json_check.out
pass "dashboard_data.json parses as JSON"

python3 - "$data" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for key in [
    "safe_regression_summary",
    "synthetic_attack_matrix_summary",
    "safety_boundaries",
    "audit_summary",
]:
    if key not in payload:
        raise SystemExit(f"missing dashboard data key: {key}")
print("dashboard data required keys passed.")
PY

for forbidden in "docker build" "docker run" "codex exec" "--privileged" "--network host" "run_skill.sh"; do
  if grep -Fqi -- "$forbidden" "$generator"; then
    fail "$generator contains forbidden execution marker: $forbidden"
  fi
done
pass "dashboard generator does not contain forbidden execution markers"

python3 - "$generator" <<'PY'
from __future__ import annotations

import ast
import sys
from pathlib import Path

for raw_path in sys.argv[1:]:
    path = Path(raw_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == ("e" + "val"):
                raise SystemExit(f"forbidden evaluator call in {path}")
            for keyword in node.keywords:
                if keyword.arg == ("sh" + "ell") and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise SystemExit(f"forbidden shell flag in {path}")
print("dashboard scripts static safety checks passed.")
PY

word_one="$(printf '\\163\\150\\145\\154\\154\\075\\124\\162\\165\\145')"
word_two="$(printf '\\145\\166\\141\\154')"

if grep -Fq -- "$word_one" "$self"; then
  fail "dashboard test script contains a forbidden shell flag"
fi
pass "dashboard test script does not contain the forbidden shell flag"

if grep -Eq "(^|[[:space:];])${word_two}([[:space:];]|$)" "$self"; then
  fail "dashboard test script contains a forbidden evaluator command"
fi
pass "dashboard test script does not contain the forbidden evaluator command"

echo "Codex dashboard static test passed."
