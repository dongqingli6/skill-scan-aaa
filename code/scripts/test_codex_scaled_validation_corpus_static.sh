#!/usr/bin/env bash
set -euo pipefail

# Big Stage 27 synthetic corpus static test.
# This test builds local zip fixtures only. It does not run Docker, Codex,
# Claude Code, strace, skills, network commands, installers, or real APIs.

python3 - <<'PY'
from __future__ import annotations

import importlib.util
import json
import shutil
import zipfile
from pathlib import Path

builder_path = Path("code/platforms/codex/scaled_validation/synthetic_corpus_builder.py")
assert builder_path.exists(), "synthetic_corpus_builder.py missing"
spec = importlib.util.spec_from_file_location("synthetic_corpus_builder", builder_path)
builder = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(builder)

root = Path("analysis_results/scaled_validation/synthetic_corpus")
if root.exists():
    shutil.rmtree(root)
manifest = builder.build_synthetic_corpus(root)
assert manifest["total_samples"] >= 12
archives = sorted(root.glob("*.zip"))
assert len(archives) >= 12

real_secret_markers = [
    "OPENAI_API_KEY=",
    "ANTHROPIC_API_KEY=",
    "GITHUB_TOKEN=",
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "/home/empty",
]
for archive_path in archives:
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert any(name.replace("\\", "/").endswith("/SKILL.md") for name in names), archive_path
        assert any(name.replace("\\", "/").endswith("/metadata.json") for name in names), archive_path
        assert any(name.replace("\\", "/").endswith("/expected_label.json") for name in names), archive_path
        text = "\n".join(archive.read(name).decode("utf-8", errors="replace") for name in names)
        expected_name = next(name for name in names if name.replace("\\", "/").endswith("/expected_label.json"))
        expected = json.loads(archive.read(expected_name).decode("utf-8"))
    for marker in real_secret_markers:
        assert marker not in text, (archive_path, marker)
    lowered = text.lower()
    if expected["expected_family"] == "benign":
        for marker in ["token", "docker.sock", "curl", "wget", "install"]:
            assert marker not in lowered, (archive_path, marker)
    if expected["expected_family"] == "attack_like":
        assert "fake" in lowered, archive_path
        assert "real_token" not in lowered, archive_path

print("Codex scaled validation corpus static test passed.")
PY

echo "Codex scaled validation corpus static test passed."
