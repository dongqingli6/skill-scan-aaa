# Codex Strace Execution Design

This document records the safe execution options for the Codex safe_skill strace harness.

## Option A: In-container strace

- Requires `strace` to already exist inside the container.
- The current `ubuntu:24.04` minimal image does not include `strace`.
- Because this stage forbids package installation, this option can only fail closed when `strace` is missing.

## Option B: strace-enabled Dockerfile

- Create a separate `Dockerfile.codex-strace-sandbox`.
- Install `strace` only after explicit user approval.
- This stage does not use this option because package installation is forbidden.

## Option C: Host strace bundle mount

- Mount `/usr/bin/strace` and its dynamic library dependencies into the container.
- This is fragile because library paths vary by host.
- This is not the default route.

## Option D: Current Safe Route

- Keep the manual script fail-closed by default.
- Add a controlled execution path gated by `STRACE_MODE=container`.
- During execution, check for `strace` inside the container before starting Codex.
- If container `strace` is missing, fail before Codex starts.
- Do not install packages, download files, or weaken Docker isolation.
