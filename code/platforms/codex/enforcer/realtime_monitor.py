"""Polling realtime monitor for Codex runtime enforcement strace output."""

from __future__ import annotations

import json
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from platforms.codex.enforcer.syscall.syscall_policy import (
        DEFAULT_POLICY_PATH,
        classify_syscall_event,
        load_syscall_policy,
    )
else:  # pragma: no cover
    from .syscall.syscall_policy import DEFAULT_POLICY_PATH, classify_syscall_event, load_syscall_policy


WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")
FAKE_PREFIXES = ("/home/codexsafe/.codex", "/home/codexsafe/.agents")
SENSITIVE_MARKERS = (
    "/.ssh",
    "/home/empty/.codex",
    "/home/empty/.agents",
    "/root/.codex",
    "/root/.agents",
    ".env",
    "token",
    "credential",
)


def syscall_name(line: str) -> str | None:
    match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\(", line)
    return match.group(1) if match else None


def quoted_path(line: str) -> str | None:
    match = re.search(r'"([^"]+)"', line)
    return match.group(1) if match else None


def open_flags(line: str) -> str | None:
    match = re.search(r'"[^"]+"\s*,\s*([^,)]+)', line)
    return match.group(1).strip() if match else None


def connect_target(line: str) -> str | None:
    inet = re.search(r'sin_addr=inet_addr\("([^"]+)"\).*?sin_port=htons\((\d+)\)', line)
    if inet:
        return f"{inet.group(1)}:{inet.group(2)}"
    if "api.openai.com" in line:
        return "api.openai.com"
    return None


def is_fake_line(line: str) -> bool:
    return any(prefix in line for prefix in FAKE_PREFIXES)


def is_write_line(name: str | None, line: str) -> bool:
    if name == "openat":
        return any(flag in line for flag in WRITE_FLAGS)
    return name in {"unlink", "rename", "chmod", "chown", "mkdir", "rmdir"}


def classify_line(line: str, source: str = "", syscall_policy: dict[str, Any] | None = None) -> dict | None:
    name = syscall_name(line)
    path = quoted_path(line)
    policy = syscall_policy or load_syscall_policy(DEFAULT_POLICY_PATH)
    event = {
        "syscall": name,
        "path": path,
        "flags": open_flags(line) if name == "openat" else None,
        "target": connect_target(line),
        "network_mode": "none",
        "line": line,
        "source": source,
    }
    finding = classify_syscall_event(event, policy)
    if finding:
        severity = finding["severity"]
        return {
            "severity": severity,
            "category": finding["category"],
            "path": finding.get("path") or finding.get("target"),
            "source": source,
            "line": line,
            "reason": finding.get("reason"),
            "matched_rule": finding.get("matched_rule"),
            "syscall": finding.get("syscall"),
            "enforcement_action": "kill_container" if severity in {"HIGH", "CRITICAL"} else "record",
        }

    return None


def scan_text(text: str, source: str = "", syscall_policy: dict[str, Any] | None = None) -> list[dict]:
    events = []
    for line in text.splitlines():
        item = classify_line(line, source=source, syscall_policy=syscall_policy)
        if item:
            events.append(item)
    return events


class PollingMonitor:
    def __init__(
        self,
        *,
        output_dir: str | Path,
        event_log: str | Path,
        container_name: str | None = None,
        runtime_response: dict[str, Any] | None = None,
        kill_on_high: bool = True,
        kill_callback: Callable[[dict], None] | None = None,
        interval_seconds: float = 1.0,
        syscall_policy_path: str | Path | None = DEFAULT_POLICY_PATH,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.event_log = Path(event_log)
        self.container_name = container_name
        self.runtime_response = runtime_response or {}
        self.kill_on_high = kill_on_high
        self.kill_callback = kill_callback
        self.interval_seconds = interval_seconds
        self.syscall_policy = load_syscall_policy(syscall_policy_path)
        self.offsets: dict[Path, int] = {}
        self.events: list[dict] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.kill_requested = False
        self.kill_error: Exception | None = None

    def start(self) -> None:
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.scan_once()

    def _run(self) -> None:
        while not self._stop.is_set():
            self.scan_once()
            time.sleep(self.interval_seconds)

    def scan_once(self) -> list[dict]:
        new_events: list[dict] = []
        for path in sorted(self.output_dir.glob("strace.log*")):
            if not path.is_file():
                continue
            previous = self.offsets.get(path, 0)
            try:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(previous)
                    chunk = handle.read()
                    self.offsets[path] = handle.tell()
            except FileNotFoundError:
                continue
            for event in scan_text(chunk, source=str(path), syscall_policy=self.syscall_policy):
                self._record(event)
                new_events.append(event)
        return new_events

    def _record(self, event: dict) -> None:
        if self.container_name:
            event.setdefault("container_name", self.container_name)
        self.events.append(event)
        with self.event_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        action_key = f"on_{event['severity'].lower()}_violation"
        policy_action = self.runtime_response.get(action_key, "kill_container")
        should_kill = (
            self.kill_on_high
            and event["severity"] in {"HIGH", "CRITICAL"}
            and policy_action == "kill_container"
            and not self.kill_requested
        )
        if should_kill:
            self.kill_requested = True
            if self.kill_callback:
                try:
                    self.kill_callback(event)
                except Exception as exc:
                    self.kill_error = exc
                    self._stop.set()
