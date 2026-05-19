# Malicious Agent Skills Bench — Codex + ASG (Claude) Integrated System

A defensive research prototype for evaluating risky AI-agent skill packages
before they are trusted by an agent runtime. **Dual-platform**: Codex-side
sandbox + Claude-side agent-in-the-loop scoring.

## Quick start (one command)

```powershell
python web_ui\app.py
```

Open `http://127.0.0.1:8765` — single portal that links to:
- ASG Dashboard (Claude-side composite scoring, 6 samples, attack chains)
- Codex Offline Dashboard (teammate's static framework)
- Skill upload / scan jobs

For the standalone ASG CLI:
```powershell
python -m asg.asg_cli scan-all-samples --enable-honeypot
python -m asg.asg_cli build-html
start asg\dashboard.html
```

See `asg/README.md` for ASG module details.

## Project origin

## Problem

Agent skills can contain hidden instructions, unsafe commands, network behavior, credential access attempts, or platform-configuration abuse. This project demonstrates a static-first and evidence-driven safety pipeline for detecting those risks.

## Highlights

- Deterministic static scanner and mock agent-assisted analysis.
- Document-behavior divergence checks.
- Synthetic runtime violation evidence.
- Controlled activation planning with human approval gates.
- Local sinkhole, fake canary credentials, and multi-session evidence.
- Human review cards, vulnerability taxonomy, and kill-chain mapping.
- Sanitized public artifacts for safe demos and evaluation.

## Architecture

`skill intake -> static scan -> agent mock analysis -> divergence analysis -> controlled evidence -> human review labels -> sanitized release artifacts`

## Safety Boundary

This is a research prototype. It does not execute real malicious skills by default. It uses synthetic and sanitized examples. Real API keys must never be used in tests. Mock/static provider paths are default. Codex / Claude provider integrations are optional or mock by default. Agent analysis cannot downgrade deterministic risk.

## Quick Start

```bash
python3 code/scripts/run_codex_open_source_release_package.py --audit --sanitize --build-docs --build-demo-materials --build-competition-pack --output analysis_results/opensource_release
bash code/scripts/run_codex_safe_regression_static_only.sh
```

## Example Outputs

Sanitized example artifacts are written to `public_artifacts/`. Stage summaries are available under `analysis_results/` for local inspection, but raw real-skill inputs are excluded from release.

## Directory Structure

- `code/platforms/codex/`: Codex-specific safety modules.
- `code/scripts/`: Static-only and controlled evidence scripts.
- `docs/`: Open-source documentation.
- `demo/`: Demo script and flow.
- `competition_materials/`: Submission-oriented writeups.
- `public_artifacts/`: Sanitized release outputs.

## Testing

```bash
bash code/scripts/test_codex_opensource_release_audit_static.sh
bash code/scripts/test_codex_opensource_release_docs_static.sh
bash code/scripts/test_codex_opensource_release_gitignore_static.sh
bash code/scripts/test_codex_opensource_release_public_artifacts_static.sh
```

## Competition Value

The project focuses on safe reproducibility, explainable evidence, layered defenses, human-review readiness, and strong boundaries around real credentials and real execution.

## Limitations

This is not a production security system. Results are prototype evidence and require human validation before operational use.

## Roadmap

- Broader curated public benchmark fixtures.
- More formal policy schemas.
- Optional isolated manual smoke tests after explicit approval.
- Better UI for review cards and evidence browsing.

## License

MIT License. Please confirm this license fits your release goals before publishing.

## Disclaimer

For defensive security research, education, and evaluation only. Do not use this project to execute malicious behavior or process real secrets.
