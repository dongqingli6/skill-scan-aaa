#!/usr/bin/env bash
set -euo pipefail

# Stage 16 safe dynamic command static guard.
# This test validates command construction only and does not run Docker.

python3 - <<'PY'
from __future__ import annotations

import ast
from pathlib import Path

runner = Path("web_ui/safe_dynamic_runner.py")
text = runner.read_text(encoding="utf-8")

assert '"--network"' in text and '"none"' in text, "network none command pieces missing"
assert ":/workspace/skill:ro" in text, "readonly sample mount missing"
assert ":/output:rw" in text, "writable output mount missing"
assert "HOME=/home/codexsafe" in text, "fake HOME missing"
assert "CODEX_HOME=/home/codexsafe/.codex" in text, "fake CODEX_HOME missing"
assert "docker_sock_mounted" in text and "False" in text, "docker socket safety marker missing"
assert "privileged" in text and "False" in text, "privileged safety marker missing"
assert "network_host" in text and "False" in text, "network host safety marker missing"
assert "timeout=TIMEOUT_SECONDS" in text, "timeout missing"
assert '"--rm"' in text, "container cleanup marker missing"
assert "uploaded_scripts_executed" in text and "False" in text, "uploaded script execution marker missing"
assert "ALLOWED_RUNTIME_IMAGES" in text, "runtime image allowlist missing"
assert "_inspect_local_runtime_image" in text, "local image preflight helper missing"
assert '"image"' in text and '"inspect"' in text, "docker image inspect preflight missing"
assert "image_present_locally" in text, "local image report field missing"
assert "image_pull_prevented" in text, "image pull prevention report field missing"
assert "docker_pull_executed" in text, "docker pull execution report field missing"
assert "runtime_image" in text, "runtime image report field missing"
assert "image_allowlisted" in text, "image allowlist report field missing"
assert "fail closed: required local runtime image is missing" in text, "missing local image fail-closed verdict missing"
assert "job.get(\"runtime_image\"" not in text and "job.get('runtime_image'" not in text, "runtime image must not be user-controlled from job"
assert "docker pull" not in text.lower(), "docker pull command must not appear"
assert text.index('["docker", "image", "inspect", image]') < text.index('"run"'), "image inspect must appear before docker run construction"
assert "_sanitized_subprocess_env" in text, "sanitized subprocess env helper missing"
assert "sanitized_subprocess_env_used" in text, "sanitized env report marker missing"
assert "host_sensitive_env_detected" in text, "host sensitive env report marker missing"
assert "host_sensitive_env_names_redacted" in text, "redacted sensitive env names marker missing"
assert "real_tokens_passed_to_container" in text, "container token pass marker missing"
assert "env=clean_env" in text, "Docker subprocess must use clean_env"
assert "env=os.environ" not in text, "host os.environ must not be passed to subprocess"
assert "os.environ.copy" not in text, "host environment copy is forbidden"
assert "source.get(name)" not in text, "sensitive environment values must not be read by name"
assert "_clean_env_has_sensitive_passthrough" in text, "clean env passthrough guard missing"
assert "_docker_command_has_sensitive_env_passthrough" in text, "Docker env passthrough guard missing"
for env_name in [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "CODEX_HOME",
    "SSH_AUTH_SOCK",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
]:
    assert env_name in text, f"sensitive env name not covered: {env_name}"

tree = ast.parse(text, filename=str(runner))
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
        raise AssertionError("eval is forbidden")
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                raise AssertionError("shell=True is forbidden")

for term in [
    "--" + "privileged",
    "--network " + "host",
    "/var/run/docker.sock",
    "codex exec",
    "strace ",
    "bash scripts/",
    "sh scripts/",
]:
    if term in text:
        raise AssertionError(f"forbidden command term found: {term!r}")

print("Codex Web UI safe dynamic command static guard passed.")
PY

echo "Codex Web UI safe dynamic command static test passed."
