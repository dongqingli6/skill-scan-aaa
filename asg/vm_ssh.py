"""Optional live SSH integration with the Claude-side VM Docker setup.

Triggers `run_skill.sh` on a remote Ubuntu VM that has:
  - Docker installed and image `claude-skill-sandbox` built
  - `~/MaliciousAgentSkillsBench-main/code/executor/run_skill.sh` present
  - Network reachable from this Windows host

Supports TWO backends:
  - paramiko (preferred if installed: pip install paramiko)
  - OpenSSH ssh.exe / scp.exe (Windows built-in, requires sshpass OR keys)

If neither is usable, callers should fall back to vm_evidence.py offline
ingestion.

Config file: `asg/vm_config.json` (NOT checked into git). Example:

    {
      "host": "192.168.61.130",
      "port": 22,
      "username": "sh",
      "password": "...",
      "remote_project_root": "~/MaliciousAgentSkillsBench-main/code",
      "remote_anthropic_api_key": "sk-LANYI-asg-...",
      "remote_anthropic_base_url": "https://lanyiapi.com"
    }
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class VMConfig:
    host: str
    port: int
    username: str
    password: str | None
    private_key_path: str | None
    remote_project_root: str
    remote_anthropic_api_key: str | None
    remote_anthropic_base_url: str | None

    @classmethod
    def from_json(cls, path: Path) -> "VMConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            host=data["host"],
            port=int(data.get("port", 22)),
            username=data["username"],
            password=data.get("password"),
            private_key_path=data.get("private_key_path"),
            remote_project_root=data.get(
                "remote_project_root",
                "~/MaliciousAgentSkillsBench-main/code",
            ),
            remote_anthropic_api_key=data.get("remote_anthropic_api_key"),
            remote_anthropic_base_url=data.get("remote_anthropic_base_url"),
        )


def _has_paramiko() -> bool:
    try:
        import paramiko  # noqa: F401

        return True
    except ImportError:
        return False


def _has_openssh() -> bool:
    """Detect Windows / Linux ssh.exe / scp.exe in PATH."""
    return _which("ssh") is not None and _which("scp") is not None


def _which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


# ============================================================
# OpenSSH backend (ssh.exe + scp.exe + sshpass-like password handling)
# ============================================================
def _openssh_common_opts() -> list[str]:
    return [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "PreferredAuthentications=password,publickey",
        "-o", "ConnectTimeout=15",
    ]


def _run_openssh_cmd(args: list[str], password: str | None = None,
                    timeout: int = 60) -> subprocess.CompletedProcess:
    """Run ssh/scp via subprocess. If password is given, use SSH_ASKPASS via
    SetX env (Windows-friendly), or stdin if available."""
    env = os.environ.copy()
    if password:
        # Use a temporary ASKPASS script
        import tempfile, stat
        askpass_path = Path(tempfile.gettempdir()) / f"asg_askpass_{os.getpid()}.bat"
        askpass_path.write_text(f"@echo {password}\n", encoding="utf-8")
        env["SSH_ASKPASS"] = str(askpass_path)
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env["DISPLAY"] = "localhost:0"  # Required by OpenSSH ASKPASS dispatch
        # On Windows we additionally try `setsid` substitute via DETACHED flag
    try:
        return subprocess.run(args, env=env, capture_output=True, text=True,
                              timeout=timeout, errors="replace")
    finally:
        if password:
            try:
                askpass_path.unlink()
            except OSError:
                pass


def _openssh_run_remote_cmd(config: "VMConfig", remote_cmd: str,
                            timeout: int = 60) -> tuple[int, str, str]:
    args = ["ssh"]
    args.extend(_openssh_common_opts())
    args.extend(["-p", str(config.port)])
    if config.private_key_path:
        args.extend(["-i", config.private_key_path])
    args.append(f"{config.username}@{config.host}")
    args.append(remote_cmd)
    result = _run_openssh_cmd(args, password=config.password, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def _openssh_scp_upload(config: "VMConfig", local: Path, remote: str,
                        recursive: bool = False, timeout: int = 120) -> tuple[int, str, str]:
    args = ["scp"]
    args.extend(_openssh_common_opts())
    if recursive:
        args.append("-r")
    args.extend(["-P", str(config.port)])
    if config.private_key_path:
        args.extend(["-i", config.private_key_path])
    args.append(str(local))
    args.append(f"{config.username}@{config.host}:{remote}")
    result = _run_openssh_cmd(args, password=config.password, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def _openssh_scp_download(config: "VMConfig", remote: str, local: Path,
                          recursive: bool = True, timeout: int = 120) -> tuple[int, str, str]:
    args = ["scp"]
    args.extend(_openssh_common_opts())
    if recursive:
        args.append("-r")
    args.extend(["-P", str(config.port)])
    if config.private_key_path:
        args.extend(["-i", config.private_key_path])
    args.append(f"{config.username}@{config.host}:{remote}")
    args.append(str(local))
    result = _run_openssh_cmd(args, password=config.password, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


PAPER_MODE_SCRIPT = r"""#!/bin/bash
# Paper-style direct script execution: no agent, no API key, just run
# the skill's bundled .py / .sh and let strace + tcpdump record syscalls.
# This is faithful to arXiv:2602.06547 §3.4 — paper does NOT invoke an
# LLM agent inside the container; it activates skills via documented
# entry points and observes behavior.

set -uo pipefail

SKILL_NAME="${1:-unknown}"
SKILL_PATH="${2:-/skill}"
LOG_DIR="${3:-/logs}"
EXEC_TIMEOUT="${4:-30}"

mkdir -p "$LOG_DIR"

echo "=== Paper-mode Docker run ==="
echo "Skill   : $SKILL_NAME"
echo "Path    : $SKILL_PATH"
echo "LogDir  : $LOG_DIR"
echo "Timeout : ${EXEC_TIMEOUT}s per script"
echo

# Start tcpdump in background (network.pcap)
tcpdump -i any -w "$LOG_DIR/network.pcap" -s 0 2>/dev/null &
TCPDUMP_PID=$!
sleep 1

STRACE_OPTS="-f -s 200 -e trace=open,openat,creat,read,write,unlink,rename,mkdir,rmdir,execve,connect,accept,sendto,recvfrom,socket"

# Collect candidate scripts (exclude the ASG runner itself)
mapfile -t SCRIPTS < <(find "$SKILL_PATH" -maxdepth 3 -type f \
    \( -name "*.py" -o -name "*.sh" -o -name "*.js" \) \
    ! -name "_asg_paper_runner.sh" | sort)

if [ ${#SCRIPTS[@]} -eq 0 ]; then
    echo "[paper-mode] No executable scripts found. Recording SKILL.md read only."
    if [ -f "$SKILL_PATH/SKILL.md" ]; then
        strace $STRACE_OPTS -o "$LOG_DIR/strace.log" \
            cat "$SKILL_PATH/SKILL.md" > "$LOG_DIR/skill_md_dump.txt" 2>&1 || true
    fi
else
    echo "[paper-mode] Found ${#SCRIPTS[@]} script(s) to execute."
    : > "$LOG_DIR/script_output.txt"
    : > "$LOG_DIR/strace.log"
    for script in "${SCRIPTS[@]}"; do
        rel="${script#$SKILL_PATH/}"
        echo "--- executing: $rel ---" | tee -a "$LOG_DIR/script_output.txt"
        case "$script" in
            *.py)
                strace $STRACE_OPTS -o "$LOG_DIR/strace.log.$$" \
                    timeout "$EXEC_TIMEOUT" python3 "$script" 2>&1 \
                    | tee -a "$LOG_DIR/script_output.txt" || true
                ;;
            *.sh)
                strace $STRACE_OPTS -o "$LOG_DIR/strace.log.$$" \
                    timeout "$EXEC_TIMEOUT" bash "$script" 2>&1 \
                    | tee -a "$LOG_DIR/script_output.txt" || true
                ;;
            *.js)
                strace $STRACE_OPTS -o "$LOG_DIR/strace.log.$$" \
                    timeout "$EXEC_TIMEOUT" node "$script" 2>&1 \
                    | tee -a "$LOG_DIR/script_output.txt" || true
                ;;
        esac
        cat "$LOG_DIR/strace.log.$$" >> "$LOG_DIR/strace.log" 2>/dev/null || true
        rm -f "$LOG_DIR/strace.log.$$"
    done
fi

# Stop tcpdump
kill -INT "$TCPDUMP_PID" 2>/dev/null || true
sleep 1

# Filesystem changes summary
find "$SKILL_PATH" -type f -newer "$LOG_DIR/network.pcap" 2>/dev/null > "$LOG_DIR/fs_modified_after_start.txt" || true

echo "{}" > "$LOG_DIR/filesystem_changes.json"
echo
echo "=== Paper-mode run complete ==="
echo "  scripts executed: ${#SCRIPTS[@]}"
echo "  log dir: $LOG_DIR"
"""


def trigger_paper_mode_run(
    config: "VMConfig",
    skill_path_local: "Path",
    timeout_seconds: int = 60,
    local_log_dir: "Path | None" = None,
) -> "dict[str, Any]":
    """SSH to VM, upload skill, run claude-skill-sandbox image with paper-style
    direct script execution (NO Claude CLI, NO API key needed).

    Records: strace.log + network.pcap + script_output.txt + filesystem_changes.json
    """
    skill_path_local = Path(skill_path_local).resolve()
    if not skill_path_local.is_dir():
        raise FileNotFoundError(f"Skill path not a directory: {skill_path_local}")
    if not _has_paramiko():
        return {
            "status": "skipped",
            "skipped_reason": "paramiko not installed",
            "local_log_dir": None,
        }
    import paramiko

    skill_name = skill_path_local.name
    local_log_dir = local_log_dir or (
        Path("analysis_results") / "asg_vm_paper" / skill_name
    )
    local_log_dir.mkdir(parents=True, exist_ok=True)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs: dict[str, Any] = {
            "hostname": config.host, "port": config.port,
            "username": config.username, "timeout": 15,
        }
        if config.password:
            connect_kwargs["password"] = config.password
        if config.private_key_path:
            connect_kwargs["key_filename"] = config.private_key_path
        client.connect(**connect_kwargs)
    except Exception as exc:
        return {"status": "ssh_connect_failed",
                "skipped_reason": f"{type(exc).__name__}: {exc}",
                "local_log_dir": None}

    try:
        # 1. Resolve upload dir + log dir on VM
        _, stdout, _ = client.exec_command(
            f"mkdir -p ~/asg_paper_uploads/{skill_name} ~/asg_paper_logs/{skill_name} "
            f"&& readlink -f ~/asg_paper_uploads/{skill_name} "
            f"&& readlink -f ~/asg_paper_logs/{skill_name}"
        )
        lines = stdout.read().decode("utf-8", errors="replace").strip().splitlines()
        if len(lines) < 2:
            return {"status": "remote_mkdir_failed", "local_log_dir": None,
                    "skipped_reason": "could not resolve remote paths"}
        remote_upload = lines[0]
        remote_logs = lines[1]
        # Clean previous log dir
        client.exec_command(f"rm -rf {remote_logs}/* && mkdir -p {remote_logs}")

        # 2. Upload skill
        sftp = client.open_sftp()
        try:
            for local_file in skill_path_local.rglob("*"):
                if local_file.is_dir():
                    continue
                rel = local_file.relative_to(skill_path_local)
                remote_path = f"{remote_upload}/{rel.as_posix()}"
                parent = "/".join(remote_path.split("/")[:-1])
                client.exec_command(f"mkdir -p {parent}")
                sftp.put(str(local_file), remote_path)
            # 3. Upload the paper-mode runner script
            runner_remote = f"{remote_upload}/_asg_paper_runner.sh"
            with sftp.open(runner_remote, "w") as f:
                f.write(PAPER_MODE_SCRIPT)
            client.exec_command(f"chmod +x {runner_remote}")
        finally:
            sftp.close()

        # 4. Run inside claude-skill-sandbox container (no Claude, just scripts)
        # Note: --cap-add SYS_ADMIN/NET_ADMIN + seccomp=unconfined are required
        # for strace + tcpdump to work inside the container.
        docker_cmd = (
            "docker run --rm "
            "--cap-add=SYS_ADMIN --cap-add=NET_ADMIN --cap-add=SYS_PTRACE "
            "--security-opt seccomp=unconfined "
            "--security-opt apparmor=unconfined "
            f"-v {remote_upload}:/skill:ro "
            f"-v {remote_logs}:/logs:rw "
            "-w /skill "
            "claude-skill-sandbox "
            "bash /skill/_asg_paper_runner.sh "
            f"'{skill_name}' '/skill' '/logs' '{timeout_seconds}'"
        )
        _, stdout, stderr = client.exec_command(
            docker_cmd, timeout=timeout_seconds + 60, get_pty=True
        )
        run_stdout = stdout.read().decode("utf-8", errors="replace")
        run_stderr = stderr.read().decode("utf-8", errors="replace")

        # 5. Pull logs back
        sftp = client.open_sftp()
        pulled = False
        try:
            try:
                sftp.stat(remote_logs)
                _, listing, _ = client.exec_command(f"ls {remote_logs}")
                for fname in listing.read().decode("utf-8", "replace").splitlines():
                    if not fname:
                        continue
                    src = f"{remote_logs}/{fname}"
                    try:
                        sftp.get(src, str(local_log_dir / fname))
                        pulled = True
                    except (OSError, IOError):
                        continue
            except FileNotFoundError:
                pass
        finally:
            sftp.close()

        (local_log_dir / "ssh_run_stdout.log").write_text(run_stdout, encoding="utf-8")
        (local_log_dir / "ssh_run_stderr.log").write_text(run_stderr, encoding="utf-8")

        return {
            "status": "completed" if pulled else "completed_no_logs",
            "local_log_dir": str(local_log_dir),
            "remote_command_preview": docker_cmd,
            "pulled_any_logs": pulled,
            "mode": "paper_no_claude",
        }
    finally:
        client.close()


def trigger_remote_run(
    config: VMConfig,
    skill_path_local: Path,
    user_prompt: str = "Read the SKILL.md and use this skill as a typical user would.",
    timeout_seconds: int = 300,
    local_log_dir: Path | None = None,
) -> dict[str, Any]:
    """SSH to the VM, upload the skill, trigger run_skill.sh, pull logs back.

    On the remote side, this script:
      1. mkdir -p ~/asg_uploads/<skill_name>
      2. SCP local skill_path -> remote location
      3. Sets ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL env (from config)
      4. Runs: bash <remote_project_root>/executor/run_skill.sh <name> <abs_path> "<prompt>"
      5. SCP back execution_logs/test/manual/<skill_name>/

    Returns a dict with status + local log directory containing the artifacts.
    """
    skill_path_local = Path(skill_path_local).resolve()
    if not skill_path_local.is_dir():
        raise FileNotFoundError(f"Skill path not a directory: {skill_path_local}")

    if not _has_paramiko():
        return {
            "status": "skipped",
            "skipped_reason": "paramiko not installed (pip install paramiko)",
            "local_log_dir": None,
        }

    import paramiko

    skill_name = skill_path_local.name
    local_log_dir = local_log_dir or (
        Path("analysis_results") / "asg_vm" / skill_name
    )
    local_log_dir.mkdir(parents=True, exist_ok=True)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs: dict[str, Any] = {
            "hostname": config.host,
            "port": config.port,
            "username": config.username,
            "timeout": 15,
        }
        if config.password:
            connect_kwargs["password"] = config.password
        if config.private_key_path:
            connect_kwargs["key_filename"] = config.private_key_path
        client.connect(**connect_kwargs)
    except Exception as exc:
        return {
            "status": "ssh_connect_failed",
            "skipped_reason": f"{type(exc).__name__}: {exc}",
            "local_log_dir": None,
        }

    try:
        # === Step 1: prepare remote upload dir ===
        remote_upload_dir = f"~/asg_uploads/{skill_name}"
        _, stdout, _ = client.exec_command(
            f"mkdir -p {remote_upload_dir} && readlink -f {remote_upload_dir}"
        )
        remote_abs = stdout.read().decode("utf-8", errors="replace").strip()
        if not remote_abs:
            return {
                "status": "remote_mkdir_failed",
                "skipped_reason": "could not resolve remote upload dir",
                "local_log_dir": None,
            }

        # === Step 2: upload skill via SFTP ===
        sftp = client.open_sftp()
        try:
            for local_file in skill_path_local.rglob("*"):
                if local_file.is_dir():
                    continue
                rel = local_file.relative_to(skill_path_local)
                remote_path = f"{remote_abs}/{rel.as_posix()}"
                parent = "/".join(remote_path.split("/")[:-1])
                client.exec_command(f"mkdir -p {parent}")
                sftp.put(str(local_file), remote_path)
        finally:
            sftp.close()

        # === Step 3: build remote run command ===
        project_root = config.remote_project_root.rstrip("/")
        # The script expects $PROJECT_ROOT and $EXECUTION_LOGS_DIR. Use
        # the same defaults that quick_execute.sh sets up.
        env_prefix_parts = [
            f"PROJECT_ROOT={project_root}",
            f"EXECUTION_LOGS_DIR={project_root}/execution_logs",
        ]
        if config.remote_anthropic_api_key:
            env_prefix_parts.append(
                f"ANTHROPIC_AUTH_TOKEN='{config.remote_anthropic_api_key}'"
            )
            env_prefix_parts.append(
                f"ANTHROPIC_API_KEY='{config.remote_anthropic_api_key}'"
            )
        if config.remote_anthropic_base_url:
            env_prefix_parts.append(
                f"ANTHROPIC_BASE_URL='{config.remote_anthropic_base_url}'"
            )
        env_prefix_parts.append(f"EXEC_TIMEOUT={timeout_seconds}")
        env_prefix_parts.append("USE_NOVA=false")  # keep NOVA off for SSH demo
        env_prefix_parts.append("NOVA_BLOCK=false")

        env_prefix = " ".join(env_prefix_parts)

        remote_cmd = (
            f"cd {project_root} && "
            f"{env_prefix} "
            f"bash executor/run_skill.sh "
            f"'{skill_name}' '{remote_abs}' "
            f"'{user_prompt}' "
            f"'asg' 'manual' 'false'"
        )

        # === Step 4: execute ===
        # run_skill.sh uses `docker run -it` so we need PTY allocation.
        _, stdout, stderr = client.exec_command(
            remote_cmd,
            timeout=timeout_seconds + 60,
            get_pty=True,
        )
        run_stdout = stdout.read().decode("utf-8", errors="replace")
        run_stderr = stderr.read().decode("utf-8", errors="replace")

        # === Step 5: pull back the logs ===
        # SFTP doesn't expand `~`, so we need an absolute path. Use the shell
        # to resolve the project root first.
        _, stdout, _ = client.exec_command(
            f"readlink -f {project_root}"
        )
        abs_project_root = stdout.read().decode("utf-8", errors="replace").strip()
        if not abs_project_root:
            abs_project_root = project_root.replace("~", f"/home/{config.username}")
        # run_skill.sh writes to $EXECUTION_LOGS_DIR/$RISK_LEVEL/$REPO_ID/<skill_name>
        # We passed RISK_LEVEL=manual, REPO_ID=asg.
        candidate_paths = [
            f"{abs_project_root}/execution_logs/manual/asg/{skill_name}",
            f"{abs_project_root}/execution_logs/test/manual/{skill_name}",
            f"{abs_project_root}/execution_logs/asg/manual/{skill_name}",
        ]

        sftp = client.open_sftp()
        pulled_any = False
        try:
            for candidate in candidate_paths:
                try:
                    sftp.stat(candidate)
                except FileNotFoundError:
                    continue
                _, listing, _ = client.exec_command(f"ls {candidate}")
                files = listing.read().decode("utf-8", errors="replace").splitlines()
                for fname in files:
                    if not fname:
                        continue
                    src = f"{candidate}/{fname}"
                    dst = local_log_dir / fname
                    try:
                        sftp.get(src, str(dst))
                        pulled_any = True
                    except (OSError, IOError):
                        continue
                if pulled_any:
                    break
        finally:
            sftp.close()

        # Also save the run stdout/stderr for forensics
        (local_log_dir / "ssh_run_stdout.log").write_text(
            run_stdout, encoding="utf-8"
        )
        (local_log_dir / "ssh_run_stderr.log").write_text(
            run_stderr, encoding="utf-8"
        )

        return {
            "status": "completed" if pulled_any else "completed_no_logs",
            "local_log_dir": str(local_log_dir),
            "remote_command_preview": remote_cmd,
            "pulled_any_logs": pulled_any,
        }
    finally:
        client.close()
