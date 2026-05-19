# Stage 22 Egress Policy Notes

Stage 22 keeps egress fully disabled for controlled dynamic inspection.

- Default network policy: deny.
- Docker network mode: `none`.
- Host network: forbidden.
- DNS: not allowed.
- Egress proxy and egress allowlist: disabled in this stage.
- No curl, wget, package install, Codex execution, or external API call is allowed in Stage 22.

Any future egress allowlist must be a separate reviewed stage with explicit approval and audit logging.
