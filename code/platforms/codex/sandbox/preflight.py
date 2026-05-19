"""Preflight validation for Codex sandbox plan-only mode."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    from platforms.codex.sandbox.sandbox_models import CodexSandboxConfig
except ImportError:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.sandbox.sandbox_models import CodexSandboxConfig


SENSITIVE_ENV_NAMES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "CODEX_HOME", "SSH_AUTH_SOCK")


def _result(warnings: List[str] | None = None, errors: List[str] | None = None, sensitive: List[str] | None = None) -> Dict[str, Any]:
    warnings = warnings or []
    errors = errors or []
    sensitive = sensitive or []
    return {"ok": not errors, "warnings": warnings, "errors": errors, "sensitive_env_names": sensitive}


def validate_sandbox_config(config: CodexSandboxConfig) -> Dict[str, Any]:
    warnings: List[str] = []
    errors: List[str] = []
    if config.dynamic_execution_enabled:
        warnings.append("dynamic_execution_enabled is true; current stage supports plan-only output.")
    if config.allow_codex_exec:
        errors.append("allow_codex_exec must remain false in plan-only mode.")
    if config.allow_network:
        errors.append("allow_network must remain false by default.")
    if config.allow_real_home:
        errors.append("allow_real_home must remain false.")
    if config.allow_real_tokens:
        errors.append("allow_real_tokens must remain false.")
    if config.allow_yolo:
        errors.append("allow_yolo must remain false.")
    if config.sandbox_mode != "read-only":
        warnings.append(f"sandbox_mode is {config.sandbox_mode!r}; expected read-only.")
    if config.approval_policy != "never":
        warnings.append(f"approval_policy is {config.approval_policy!r}; expected never.")
    return _result(warnings, errors)


def validate_fake_home_paths(paths: Dict[str, Any]) -> Dict[str, Any]:
    errors = []
    for key in ("fake_home", "fake_codex_home", "fake_agents_dir", "sample_mount", "output_dir", "logs_dir", "config_toml_path"):
        if not paths.get(key):
            errors.append(f"missing path: {key}")
    return _result(errors=errors)


def validate_no_real_home_reference(paths: Dict[str, Any]) -> Dict[str, Any]:
    warnings: List[str] = []
    errors: List[str] = []
    home = Path.home().resolve()
    codex_home = home / ".codex"
    agents_home = home / ".agents"
    for key, value in paths.items():
        if not isinstance(value, str):
            continue
        candidate = Path(value).expanduser().resolve()
        if candidate == home:
            errors.append(f"{key} references real HOME")
        if candidate == codex_home or codex_home in candidate.parents:
            errors.append(f"{key} references real ~/.codex")
        if candidate == agents_home or agents_home in candidate.parents:
            errors.append(f"{key} references real ~/.agents")
    return _result(warnings, errors)


def validate_no_sensitive_env() -> Dict[str, Any]:
    sensitive = sorted(name for name in SENSITIVE_ENV_NAMES if os.environ.get(name))
    warnings = [f"sensitive environment variable is set: {name}" for name in sensitive]
    return _result(warnings=warnings, sensitive=sensitive)


def validate_skill_path_inside_allowed_root(skill_path: str | Path, allowed_root: str | Path) -> Dict[str, Any]:
    skill = Path(skill_path).resolve()
    root = Path(allowed_root).resolve()
    if skill == root or root in skill.parents:
        return _result()
    return _result(errors=[f"skill path is outside allowed root: {skill}"])


def validate_no_symlink_escape(root: str | Path) -> Dict[str, Any]:
    warnings: List[str] = []
    root_path = Path(root).resolve()
    for item in root_path.rglob("*"):
        if item.is_symlink():
            warnings.append(f"symlink present and must not be followed: {item}")
    return _result(warnings=warnings)


def validate_dynamic_disabled_by_default(config: CodexSandboxConfig) -> Dict[str, Any]:
    if config.dynamic_execution_enabled:
        return _result(errors=["dynamic execution must be disabled by default"])
    return _result()


def combine_results(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    warnings: List[str] = []
    errors: List[str] = []
    sensitive: List[str] = []
    for result in results:
        warnings.extend(result.get("warnings", []))
        errors.extend(result.get("errors", []))
        sensitive.extend(result.get("sensitive_env_names", []))
    return _result(warnings=warnings, errors=errors, sensitive=sorted(set(sensitive)))
