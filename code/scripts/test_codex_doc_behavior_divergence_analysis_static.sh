#!/usr/bin/env bash
set -euo pipefail

# Big Stage 26 analysis static test.
# This test does not run Docker, Codex, Claude Code, strace, real skills,
# network commands, uploaded scripts, installers, or real APIs.

python3 - <<'PY'
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

runner = Path("code/scripts/run_codex_doc_behavior_divergence_analysis.py")
assert runner.exists(), "runner missing"
text = runner.read_text(encoding="utf-8")
assert "subprocess" not in text
assert "shell=True" not in text
assert "codex exec" not in text.lower()
assert "claude code" not in text.lower()
assert "strace " not in text.lower()
assert "run_skill.sh" not in text.lower()
assert "install.sh" not in text.lower()
assert "setup.sh" not in text.lower()
assert "curl " not in text.lower()
assert "wget " not in text.lower()
assert "--include-all-real-skills" in text

tree = ast.parse(text, filename=str(runner))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True forbidden")

root = Path("code/platforms/codex/doc_behavior_diff")
for path in root.glob("*.py"):
    module_text = path.read_text(encoding="utf-8")
    assert "subprocess" not in module_text, path
    assert "shell=True" not in module_text, path
    module_tree = ast.parse(module_text, filename=str(path))
    for node in ast.walk(module_tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            raise AssertionError(f"eval forbidden in {path}")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    raise AssertionError(f"shell=True forbidden in {path}")

sys.path.insert(0, str(root.resolve()))
spec = importlib.util.spec_from_file_location("divergence_analyzer", root / "divergence_analyzer.py")
analyzer = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(analyzer)
assert analyzer.DEFAULT_REAL_SKILLS == [
    "implementation-guide.zip",
    "logging-best-practices.zip",
    "val-town-cli.zip",
    "ideation.zip",
    "react-effect-patterns.zip",
]

summary = analyzer.analyze_doc_behavior_divergence(
    repo_root=Path(".").resolve(),
    inbox=Path("analysis_results/real_skill_intake/inbox").resolve(),
    sample_names=list(analyzer.DEFAULT_REAL_SKILLS),
)
assert summary["total_samples"] == 5
assert summary["docker_executed"] is False
assert summary["codex_executed"] is False
assert summary["claude_code_executed"] is False
assert summary["strace_executed"] is False
assert summary["real_skill_executed"] is False
assert summary["real_api_called"] is False
assert summary["network_enabled"] is False
assert all(result["claims"]["skill_md_treated_as_untrusted"] for result in summary["results"])
assert any(result["summary"]["decision"] in ("blocked", "manual_review") for result in summary["results"])

missing_summary = analyzer.analyze_doc_behavior_divergence(
    repo_root=Path(".").resolve(),
    inbox=Path("analysis_results/real_skill_intake/inbox").resolve(),
    sample_names=["missing-skill.zip"],
)
assert missing_summary["evidence_missing"] is True
assert missing_summary["results"][0]["summary"]["decision"] in ("manual_review", "note")

print("Codex doc-behavior divergence analysis static test passed.")
PY

echo "Codex doc-behavior divergence analysis static test passed."
