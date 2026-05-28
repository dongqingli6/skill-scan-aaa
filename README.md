# SkillSentinel — Agent Skill Security Dashboard

A defensive research prototype for evaluating risky AI-agent skill packages
before they are trusted by an agent runtime. **Dual-platform**: Codex-side
sandbox + Claude-side agent-in-the-loop scoring.

## Quick start (one command)

```powershell
python web_ui\app.py
```

Open `http://127.0.0.1:8765` — single portal that links to:
- ASG Dashboard (Claude-side composite scoring, 7 samples, attack chains)
- Codex Offline Dashboard (teammate's static framework)
- Skill upload / scan jobs

For the standalone ASG CLI:
```powershell
python -m asg.asg_cli scan-all-samples --enable-honeypot
python -m asg.asg_cli build-html
python code/scripts/release_safety_check.py
start asg\dashboard.html
```

See `asg/README.md` for ASG module details.

## Level3 Visual Dashboard

Level3 adds a local visual dashboard for making existing security evidence
easier to inspect. It focuses on risk overview, score sources, risk dimensions,
dynamic behavior timeline, rule explanations, and static/dynamic comparison.

## Level3.1 Security Review Dashboard

Level3.1 shifts the dashboard from a visual overview into a security review
workspace for maintainers, developers, and security reviewers. It is designed
for triage and evidence inspection rather than visual promotion.

The review interface adds:

- Security Review Dashboard header with skill name, risk level, analysis mode,
  generated time, and data source.
- Review Decision Panel with suggested decision and manual review status.
- Key Risk Summary with top risks, severe evidence, and security flags.
- Evidence Timeline filtering by severity, event type, and keyword search.
- Rule Findings filtering by severity, source, and keyword search.
- Static vs Dynamic Comparison with reviewer-friendly wording.
- Recommended Actions focused on containment and approval decisions.
- Raw Evidence Data with formatted JSON and copy support.
- Security Review Mode, which defaults to hiding INFO-level noise and focusing
  on HIGH/MEDIUM review items.
- DEMO data labeling so synthetic dashboard data is not mistaken for verified
  runtime evidence.

Generate demo data and preview the dashboard:

```bash
python3 tools/generate_dashboard_data.py examples/demo-risky-skill
python3 -m http.server 8000
```

Open `http://localhost:8000/dashboard/`.

The dashboard reads `artifacts/demo-risky-skill/dashboard_data.json`. The demo
data is explicitly labeled with `analysis_mode: demo`; it is only for showing
the dashboard structure and should not be presented as a verified VM Mode C
execution result.

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
- ASG level_3 Release Safety Check before GitHub publishing.
- Level3 visual dashboard with risk cards, dimensions, timeline, findings, and comparison views.

## Architecture

`skill intake -> static scan -> agent mock analysis -> divergence analysis -> controlled evidence -> human review labels -> sanitized release artifacts`

## Safety Boundary

This is a research prototype. It does not execute real malicious skills by default. It uses synthetic and sanitized examples. Real API keys must never be used in tests. Mock/static provider paths are default. Codex / Claude provider integrations are optional or mock by default. Agent analysis cannot downgrade deterministic risk.

ASG level_3 adds a release safety check for open-source packaging:

```bash
python code/scripts/make_clean_release.py
python code/scripts/release_safety_check.py --root dist/SKILL-Codex-release-clean
python code/scripts/release_safety_check.py
```

It scans for real API keys, GitHub/AWS tokens, SSH passwords, private keys,
`asg/vm_config.json`, full honeypot markers in public artifacts, large files,
packet captures, logs, caches, and missing `.gitignore` protections. Reports are
written to `analysis_results/release_safety_check/`. The clean release builder
keeps public artifacts separate from private VM evidence and excludes
honeypot bundles, fake HOME trees, packet captures, local VM configs, and raw
quarantine outputs.

VM Mode C code path is implemented; real VM validation requires `paramiko` and a
configured VM.

## Quick Start

```bash
python3 code/scripts/run_codex_open_source_release_package.py --audit --sanitize --build-docs --build-demo-materials --build-competition-pack --output analysis_results/opensource_release
bash code/scripts/run_codex_safe_regression_static_only.sh
```

## Example Outputs

Sanitized example artifacts are written to `public_artifacts/`. Level summaries are available under `analysis_results/` for local inspection, but raw real-skill inputs are excluded from release.

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
