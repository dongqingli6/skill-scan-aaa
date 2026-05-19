# Stage 22 Seccomp Policy Notes

Stage 22 records seccomp as a hardening requirement for future runtime work. The current prototype does not install or fetch a custom seccomp profile during static hardening.

- Default stance: prefer Docker default seccomp or a stricter local profile before any broader dynamic rollout.
- Network remains denied with `--network none`; seccomp is not used as the primary network boundary.
- No Stage 22 test runs real samples, Codex, strace, install commands, or uploaded scripts.
- Future work should add a checked-in local seccomp profile and require it in the Docker command builder after compatibility validation.
