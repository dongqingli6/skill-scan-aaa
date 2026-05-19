#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import importlib.util
from pathlib import Path

path = Path("code/platforms/codex/human_review_labeling/taxonomy.py")
assert path.exists()
spec = importlib.util.spec_from_file_location("taxonomy", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
text = str(module.taxonomy_json())
for group in ["Credential", "Network", "Execution", "Docker", "Platform", "Prompt injection", "Multi-session"]:
    assert group in text
for label in ["CRED_ACCESS", "CRED_EXFIL", "DOCKER_SOCK", "PLATFORM_CONFIG_WRITE", "PROMPT_INJECTION", "SHADOW_FEATURE", "DELAYED_TRIGGER", "BLOCKED_BY_POLICY"]:
    assert label in module.all_labels(), label
print("Codex human review taxonomy static test passed.")
PY

echo "Codex human review taxonomy static test passed."
