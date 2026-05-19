"""Runtime executor for safe_skill-only Codex enforcement mode."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:  # pragma: no cover
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.enforcer.docker_command_builder import DEFAULT_IMAGE, FAKE_HOME_INIT_SCRIPT
    from platforms.codex.enforcer.runtime_policy import resolve_repo_path, validate_skill_path
else:  # pragma: no cover
    from .docker_command_builder import DEFAULT_IMAGE, FAKE_HOME_INIT_SCRIPT
    from .runtime_policy import resolve_repo_path, validate_skill_path


SENSITIVE_ENV = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "CODEX_HOME", "SSH_AUTH_SOCK")
TRACE_SET = "execve,openat,socket,connect,sendto,recvfrom,unlink,rename,chmod,chown,mkdir,rmdir,clone"


def check_sensitive_env_absent() -> None:
    present = [name for name in SENSITIVE_ENV if os.environ.get(name)]
    if present:
        raise RuntimeError(f"sensitive environment variables are present: {', '.join(present)}")


def check_docker_access(docker_cmd: str) -> None:
    if docker_cmd != "docker":
        raise RuntimeError("enforce mode only supports DOCKER_CMD=docker; sudo docker is forbidden")
    subprocess.run([docker_cmd, "ps"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _safe_subprocess_env(output_dir: Path) -> dict[str, str]:
    docker_home = output_dir / "docker_client_home"
    docker_config = docker_home / ".docker"
    docker_config.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(docker_home),
        "DOCKER_CONFIG": str(docker_config),
    }


def validate_docker_command(command: list[str]) -> None:
    preview = " ".join(shlex.quote(part) for part in command)
    forbidden = ["--privileged", "--network host", "/var/run/docker.sock", "sudo docker", "sudo -n docker"]
    found = [item for item in forbidden if item in preview]
    if found:
        raise RuntimeError(f"forbidden Docker command fragment found: {found}")
    if "--network none" not in preview:
        raise RuntimeError("Docker command must use --network none")
    if "--read-only" not in command:
        raise RuntimeError("Docker command must use --read-only")
    if "--cap-drop" not in command or "ALL" not in command:
        raise RuntimeError("Docker command must use --cap-drop ALL")
    if "no-new-privileges" not in command:
        raise RuntimeError("Docker command must use no-new-privileges")
    required_mounts = [":/workspace/safe_skill:ro", ":/output:rw", ":/opt/codex-bundle:ro"]
    for mount in required_mounts:
        if mount not in preview:
            raise RuntimeError(f"required mount missing from Docker command: {mount}")


def build_enforced_docker_run_command(
    *,
    policy: dict[str, Any],
    skill_path: str | Path,
    output_dir: str | Path,
    codex_bundle_ro: str | Path,
    image: str = DEFAULT_IMAGE,
    timeout_seconds: int = 60,
    docker_cmd: str = "docker",
    container_name: str | None = None,
    seccomp_profile: str | Path | None = None,
    apparmor_profile: str | None = None,
) -> dict[str, Any]:
    if seccomp_profile or apparmor_profile:
        raise RuntimeError("seccomp/AppArmor hardening profiles are currently plan-only and are not enabled for enforce mode")
    decision = validate_skill_path(policy, skill_path)
    if not decision.allowed:
        raise RuntimeError(decision.reason)
    sample = resolve_repo_path(skill_path)
    output = resolve_repo_path(output_dir)
    bundle = resolve_repo_path(codex_bundle_ro)
    output.mkdir(parents=True, exist_ok=True)
    if not bundle.is_dir():
        raise RuntimeError(f"Codex bundle directory does not exist: {bundle}")
    if not sample.is_dir():
        raise RuntimeError(f"skill path does not exist: {sample}")

    name = container_name or f"codex-enforce-safe-skill-{uuid.uuid4().hex[:12]}"
    prompt = "List the available safe skill files and summarize the safe skill in one sentence. Do not modify files. Do not run scripts."
    inner = (
        FAKE_HOME_INIT_SCRIPT
        +
        "if ! command -v strace >/dev/null 2>&1; then "
        "echo 'container strace is not available; refusing before Codex execution' >&2; exit 42; "
        f"fi; timeout {int(timeout_seconds)} strace -ff -o /output/strace.log -e trace={TRACE_SET} \"$@\""
    )
    command = [
        docker_cmd,
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(policy.get("docker_policy", {}).get("pids_limit", 256)),
        "--memory",
        str(policy.get("docker_policy", {}).get("memory_limit", "1g")),
        "--cpus",
        str(policy.get("docker_policy", {}).get("cpus", "1.0")),
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--tmpfs",
        "/home/codexsafe:rw,nosuid,nodev,uid=1000,gid=1000,mode=700",
        "-e",
        "HOME=/home/codexsafe",
        "-e",
        "CODEX_HOME=/home/codexsafe/.codex",
        "-e",
        "PATH=/opt/codex-bundle/bin:/usr/local/bin:/usr/bin:/bin",
        "-v",
        f"{sample}:/workspace/safe_skill:ro",
        "-v",
        f"{output}:/output:rw",
        "-v",
        f"{bundle}:/opt/codex-bundle:ro",
        image,
        "/bin/bash",
        "-lc",
        inner,
        "--",
        "codex",
        "exec",
        "--sandbox",
        "read-only",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--ephemeral",
        prompt,
    ]
    validate_docker_command(command)
    return {
        "container_name": name,
        "command": command,
        "command_preview": " ".join(shlex.quote(part) for part in command),
        "output_dir": str(output),
        "sample_path": str(sample),
        "codex_bundle_ro": str(bundle),
    }


def start_container(command: list[str], output_dir: str | Path) -> subprocess.Popen[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stdout = (out / "docker_run_stdout.txt").open("w", encoding="utf-8")
    stderr = (out / "docker_run_stderr.txt").open("w", encoding="utf-8")
    env = _safe_subprocess_env(out)
    return subprocess.Popen(command, stdout=stdout, stderr=stderr, text=True, env=env)


def wait_with_timeout(process: subprocess.Popen[str], timeout_seconds: int) -> tuple[int | None, bool]:
    try:
        return process.wait(timeout=timeout_seconds + 20), False
    except subprocess.TimeoutExpired:
        return None, True


def kill_container(docker_cmd: str, container_name: str, output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    env = _safe_subprocess_env(out)
    result = subprocess.run(
        [docker_cmd, "kill", container_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    kill_result = {
        "container_name": container_name,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    if result.returncode != 0:
        raise RuntimeError(f"docker kill failed for {container_name}: {result.stderr.strip()}")
    return kill_result


def confirm_no_container_remains(docker_cmd: str, container_name: str, output_dir: str | Path) -> bool:
    env = _safe_subprocess_env(Path(output_dir))
    result = subprocess.run(
        [docker_cmd, "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    return container_name not in result.stdout.splitlines()


def collect_logs(output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    return {
        "stdout": str(out / "docker_run_stdout.txt"),
        "stderr": str(out / "docker_run_stderr.txt"),
    }


def monotonic_seconds() -> float:
    return time.monotonic()
