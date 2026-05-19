from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


FAKE_CONTAINER_NAME = "codex-synthetic-violation-container"


def synthetic_event(event_id: str, event_type: str, observed_action: str, target: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sample_name": "synthetic_runtime_violation_sample",
        "container_name": FAKE_CONTAINER_NAME,
        "event_type": event_type,
        "observed_action": observed_action,
        "target": target,
        "source": "stage24_synthetic_event_matrix",
        "dry_run": True,
        "synthetic": True,
        "evidence": {
            "description": "Synthetic event only; no real container, network, token, or host secret was touched.",
            "real_action_performed": False,
        },
    }


def synthetic_event_matrix() -> list[dict[str, Any]]:
    return [
        synthetic_docker_sock_access(),
        synthetic_outbound_network_attempt(),
        synthetic_sensitive_env_exposure(),
        synthetic_forbidden_path_read(),
        synthetic_uploaded_script_execution_attempt(),
        synthetic_privileged_request(),
        synthetic_host_network_request(),
        synthetic_docker_pull_attempt(),
        synthetic_codex_exec_attempt(),
        synthetic_strace_attempt(),
    ]


def synthetic_docker_sock_access() -> dict[str, Any]:
    return synthetic_event("synthetic-docker-sock-access", "docker_socket_access", "open", "/var/run/docker.sock")


def synthetic_outbound_network_attempt() -> dict[str, Any]:
    return synthetic_event("synthetic-outbound-network-attempt", "outbound_network_attempt", "connect", "198.51.100.10:443")


def synthetic_sensitive_env_exposure() -> dict[str, Any]:
    return synthetic_event("synthetic-sensitive-env-exposure", "real_token_exposure", "read_env", "OPENAI_API_KEY")


def synthetic_forbidden_path_read() -> dict[str, Any]:
    return synthetic_event("synthetic-forbidden-path-read", "forbidden_path_read", "read", "/home/user/.ssh/id_rsa")


def synthetic_uploaded_script_execution_attempt() -> dict[str, Any]:
    return synthetic_event("synthetic-uploaded-script-execution", "uploaded_script_execution_attempt", "exec", "/workspace/skill/run_skill.sh")


def synthetic_privileged_request() -> dict[str, Any]:
    return synthetic_event("synthetic-privileged-request", "privileged_container_requested", "docker_run_flag", "--privileged")


def synthetic_host_network_request() -> dict[str, Any]:
    return synthetic_event("synthetic-host-network-request", "host_network_requested", "docker_run_flag", "--network host")


def synthetic_docker_pull_attempt() -> dict[str, Any]:
    return synthetic_event("synthetic-docker-pull-attempt", "docker_pull_attempt", "image_pull", "example/image:latest")


def synthetic_codex_exec_attempt() -> dict[str, Any]:
    return synthetic_event("synthetic-codex-exec-attempt", "codex_exec_attempt", "exec", "codex exec")


def synthetic_strace_attempt() -> dict[str, Any]:
    return synthetic_event("synthetic-strace-attempt", "strace_attempt", "exec", "strace")
