# Egress Proxy / Allowlist Design

## Current Boundary

The current Codex runtime enforcement prototype uses Docker `--network none` by
default. This remains the safest default because a network-capable skill can
exfiltrate prompts, repository content, credentials, host metadata, or runtime
evidence if any boundary is misconfigured.

This stage does not enable network access. It only defines a future design for
controlled-network experiments.

## Why Direct Network Access Is Not Acceptable

Direct Docker networking would make outbound connections difficult to audit and
hard to constrain per skill. It would also make it easier for untrusted skill
content to contact arbitrary hosts, download additional payloads, or leak
sensitive data. For that reason, `--network none` remains the default runtime
policy.

## Future Controlled Egress Model

If network access is ever required, the container should not receive open
internet access. It should route all outbound traffic through an egress proxy
that enforces a deny-by-default policy.

Required proxy capabilities:

- DNS allowlist.
- HTTP/HTTPS allowlist.
- Request logging.
- Deny-by-default behavior.
- Per-skill network policy.
- Rate limiting.
- Audit log generation and retention.
- No credential leakage checks before forwarding requests.

## Policy Requirements

The policy must start from deny all. Domain allowlists must be reviewed by a
human and tied to a specific skill test purpose. Placeholder domains such as
`api.openai.com`, `registry.npmjs.org`, `pypi.org`, and
`files.pythonhosted.org` are not enabled by default.

## Current Stage

Current status:

- No network is enabled.
- Docker command preview defaults to `network_mode: none`.
- `controlled` network mode is a preview-only design marker.
- No Docker containers, Codex processes, strace runs, or samples are executed by
  this design stage.
- Malicious samples remain prohibited.
