# Codex Runtime Security Dashboard

This directory contains an offline HTML dashboard for the Codex Runtime
Security Prototype.

Generated files:

- `index.html`
- `dashboard_data.json`
- `style.css`

The dashboard is generated only from existing JSON and Markdown results. It
does not run Docker, Codex, strace, real samples, network-enabled commands, or
real-token workflows. It does not reference external CDN assets.

Regenerate locally with:

```bash
python3 code/scripts/generate_codex_runtime_security_dashboard.py
```
