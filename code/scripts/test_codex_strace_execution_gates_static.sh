#!/usr/bin/env bash
set -euo pipefail

script="code/scripts/run_codex_docker_safe_smoke_strace_MANUAL.sh"

bash -n "$script"

grep -F "EXECUTE_STRACE_SMOKE" "$script" >/dev/null
if grep -F "strace execution is not enabled in this stage; preview template only" "$script" >/dev/null; then
  echo "permanent strace template refusal is still present" >&2
  exit 1
fi

grep -F "code/platforms/codex/examples/safe_skill" "$script" >/dev/null
grep -F "prompt_injection_skill" "$script" >/dev/null
grep -F "script_risk_skill" "$script" >/dev/null
grep -F "agents_pollution_sample" "$script" >/dev/null
grep -F "malicious" "$script" >/dev/null
grep -F "data/malicious_skills.csv" "$script" >/dev/null
grep -F "data/skills_dataset.csv" "$script" >/dev/null

grep -F -- "--network none" "$script" >/dev/null
grep -F ":ro" "$script" >/dev/null
grep -F ":rw" "$script" >/dev/null

for bad in "--privileged" "--network host" "--yolo" "danger-full-access" "dangerously" "curl" "wget" "apt install" "npm install" "pip install"; do
  if grep -F -- "$bad" "$script" >/dev/null; then
    echo "forbidden pattern found in strace manual script: $bad" >&2
    exit 1
  fi
done

echo "Codex strace execution gate static test passed."
