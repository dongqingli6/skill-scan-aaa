# Stage 22 AppArmor Policy Notes

Stage 22 records AppArmor as a deployment hardening layer, not as a new runtime dependency.

- Default stance: prefer a local AppArmor profile when the host supports it.
- The prototype still relies on deny-by-default runtime controls: no host network, no docker.sock, no privileged mode, read-only sample mount, fake HOME, fake CODEX_HOME, and sanitized subprocess environment.
- No Stage 22 command opens network access or executes real skill scripts.
- Future work should validate a local AppArmor profile on the target host before enforcing it in all Docker runs.
