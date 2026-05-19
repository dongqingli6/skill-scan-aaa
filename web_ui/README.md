# Local Web UI / Skill Submission Portal

This is a local prototype UI for the Codex Runtime Security Prototype. It is
not a public service and must only bind to `127.0.0.1`.

Start it from the repository root:

```bash
python3 web_ui/app.py
```

Open:

```text
http://127.0.0.1:8765
```

## Workflow

1. Upload a `.zip`, `.tar.gz`, or `.tgz` skill package.
2. Enter a skill name and optional note.
3. The portal creates a job under `analysis_results/web_ui_jobs/<job_id>/`.
4. The upload is safely extracted into `uploaded_skill/`.
5. Use **Run Static Scan** to generate a prototype static report.
6. Use **Run Static + Safe Dynamic Plan** to generate a plan-only dynamic gate
   result.
7. Use **View Report** or **Download Job JSON** to inspect outputs.

## Safety Boundary

- no real tokens
- no HOME credential reads
- no docker socket mount
- no privileged container
- no host network mode
- network none by default
- dynamic execution is plan-only / fail-closed in this first UI prototype
- local only

The prototype adapter checks the uploaded file list, requires safe archive
paths, rejects symlinks and hardlinks in tar archives, checks for `SKILL.md`,
and scans text files for selected risky strings. It does not execute uploaded
files and does not run Docker, Codex, strace, dependency installers, or network
downloads.

## Web UI Usability Polish and False Positive Reduction

Stage 14 adds clearer human-readable job and report summaries, report download
links for static report Markdown / JSON and dynamic plan Markdown / JSON,
local job deletion with confirmation, and an uploaded skill file tree preview
limited to 100 relative paths.

The static adapter also has heuristic documentation-only / negative context
suppression for simple text such as "does not use docker.sock" or "does not
access ~/.ssh". Suppressed documentation-only matches are shown in the static
report but are not counted toward HIGH / CRITICAL risk summary totals.

This is a heuristic false-positive reduction, not a production classifier.
Dynamic detection remains plan-only / fail-closed. The UI still does not run
Docker, Codex, strace, uploaded files, real samples, network-enabled workflows,
or real-token workflows.

## Web UI Real Static Scanner Integration

Stage 15 connects the **Run Static Scan** button to the repository's existing
Codex static scanner when it is available. The integration first tries the
safe Python module entrypoint
`platforms.codex.static_scan.build_static_scan_result`. If the real scanner is
unavailable or incompatible, the UI falls back to the prototype adapter.

Reports include:

- `scanner_mode`: `real_static_scanner`, `prototype_static_adapter`, or
  `fallback_static_adapter`
- `risk_summary`
- normalized `findings`
- `files_scanned`
- `skill_found`
- scanner warnings and errors

This is a research prototype integration, not a production scanning platform.
The stage still does not run Docker, Codex, strace, uploaded files, real
samples, network-enabled workflows, or real-token workflows.

## Web UI Safe Dynamic Execution Gate

Stage 16 adds a fail-closed safe dynamic execution gate for benign uploaded
skills. Static scanning must be completed, HIGH / CRITICAL findings must be
zero, the uploaded skill path must remain under the job's `uploaded_skill/`
directory, required safety boundaries must be present, and the user must
explicitly confirm safe dynamic execution.

The first runner is container-based benign inspection only. It lists files and
greps selected suspicious patterns under the read-only uploaded skill mount. It
does not execute uploaded scripts, Codex, strace, real malicious samples, or
network-enabled workflows.

Required controls include Docker network none, fake HOME / CODEX_HOME,
read-only sample mount, writable output mount, no docker socket, no privileged
mode, no host network mode, no real tokens, timeout, runtime monitor
requirement, and fail-closed default behavior.

## Stage 17 Manual Web UI Gate Verification and Benign Docker Smoke

Stage 17 manually verified the local Web UI dynamic gate with
`demo_clean_skill.zip`. The benign skill uploaded successfully, the static scan
completed with zero critical, high, medium, low, and informational findings,
and the Dynamic Execution Gate reported `allowed`.

Safe dynamic execution still requires explicit human confirmation before the
runner can proceed. The benign Docker no-network smoke completed successfully
after confirmation. Docker was run with `--network none`, a read-only uploaded
skill mount, a writable output mount, fake HOME / CODEX_HOME, no docker socket
mount, no privileged mode, no host network mode, no real tokens, no Codex /
`codex exec`, no strace, no uploaded script execution, and no malicious sample
execution.

The runtime image path now performs a local `docker image inspect` before
`docker run`. Automatic Docker image pulls are forbidden; if the required
allowlisted image is not present locally, the runner fails closed. The verified
runtime image was `python:3.11-slim` with `image_allowlisted=true`,
`image_present_locally=true`, `docker_pull_executed=false`,
`container_started=true`, and `container_removed=true`.

This system remains a research prototype, not a production security platform.

## Stage 21 Low-risk Real Skill Controlled Dynamic Inspection

Stage 21 prepares a controlled dynamic inspection runner for low-risk real
skills. Only real skills with C0 H0 M0 L0 may enter this stage. The current
allowlist is limited to `ideation.zip` and `react-effect-patterns.zip`.

The runner is designed for no-network benign inspection only: file tree review
and `SKILL.md` reading inside a constrained container. It must not execute real
skill scripts, Codex, strace, dependency installers, upload scripts, or network
tools. MEDIUM / HIGH / CRITICAL samples do not enter this stage:
`implementation-guide.zip` remains blocked, while `logging-best-practices.zip`
and `val-town-cli.zip` remain manual review only.

Required controls include local image inspect before run, no automatic image
pulls, `--network none`, fake HOME, fake CODEX_HOME, sanitized subprocess env,
read-only sample mount, writable output mount, no docker.sock, no privileged
mode, no network host, and no real tokens. Real benign Docker inspection still
requires explicit human approval before running.

## Stage 19 Real Skill Intake / Static-only Evaluation

Stage 19 adds a static-only intake path for real skill archives. Real skill
packages must first be manually placed in
`analysis_results/real_skill_intake/inbox/`. The intake flow computes a sha256
manifest, safely extracts the archive into quarantine, records file metadata
and a file tree, runs static scanning, and writes a dynamic gate plan-only
report.

The quarantine layout is:

- `analysis_results/real_skill_intake/inbox/`
- `analysis_results/real_skill_intake/quarantine/`
- `analysis_results/real_skill_intake/manifests/`
- `analysis_results/real_skill_intake/reports/`

Stage 19 does not execute real skills, run Docker dynamic smoke, run Codex,
run strace, pass real tokens, read real HOME credentials, or run uploaded
scripts. HIGH / CRITICAL findings block any later dynamic gate. Low-risk real
skills still require manual review before Stage 21.

## Stage 20 Real Skill Batch Static Evaluation + Risk Dashboard

Stage 20 generated a batch static dashboard for the five real skill archives in
the Stage 19 intake set. The evaluation remained static-only:
`processed=5`, `failed=0`.

Results:

- `implementation-guide.zip`: HIGH=4, MEDIUM=1, classified `blocked`.
- `logging-best-practices.zip`: MEDIUM=1, classified `manual_review`.
- `val-town-cli.zip`: MEDIUM=1, classified `manual_review`.
- `ideation.zip`: zero findings, classified `stage21_candidate`.
- `react-effect-patterns.zip`: zero findings, classified `stage21_candidate`.

The dashboard artifacts are under
`analysis_results/real_skill_batch_static_dashboard/`. Stage 20 did not run
Docker, Codex, strace, or any real skill. Any Stage 21 dynamic check requires
explicit human approval and must keep no-network, fake HOME, fake CODEX_HOME,
no docker.sock, no privileged mode, and no network host.

## Stage 18 Negative Gate Verification / Dangerous Synthetic Block Test

Stage 18 adds a dangerous synthetic block regression for the Web UI gate. The
synthetic package is a test-only archive containing a single text `SKILL.md`
with inert dangerous strings such as `docker.sock`, token environment names,
SSH key path text, download-tool names, and credential/exfiltration wording.

The synthetic skill is not executed. It is used only to verify that static
scanning can produce HIGH / CRITICAL findings, the Dynamic Gate reports
`denied`, HIGH / CRITICAL findings cannot be overridden by human confirmation,
and `run_safe_dynamic_scan` still fails closed if called directly. The
verification records no container start, no Codex execution, no strace
execution, no uploaded script execution, and no real malicious sample
execution.

This system remains a research prototype, not a production security platform.
Stage 21 completed result: only `ideation.zip` and `react-effect-patterns.zip` were inspected, and both finished with `final_verdict=controlled no-network benign inspection completed`. `implementation-guide.zip` stayed blocked because of HIGH findings. `logging-best-practices.zip` and `val-town-cli.zip` stayed manual review because of MEDIUM findings.

Verified controls: Docker used `--network none`; local `docker image inspect` ran before `docker run`; automatic image pulls were forbidden with `docker_pull_executed=false`; the sample mount was read-only; the output mount was writable; fake HOME and fake CODEX_HOME were used; sanitized subprocess env was used; docker.sock was not mounted; privileged mode and network host mode were not used; real tokens were not passed; Codex / `codex exec` was not run; strace was not run; real skill scripts were not executed. The system remains a research prototype, not a production security system.
## Stage 22 Runtime Hardening / Runtime Policy Strengthening

Stage 22 strengthens runtime policy, audit fields, and static tests only. It does not run real samples, does not run Docker smoke, does not run Codex, does not run strace, and does not execute real skill scripts.

- Network defaults to deny; Docker dynamic inspection must use `--network none`.
- Host network, docker.sock mounts, privileged containers, Docker pull, real HOME, real CODEX_HOME, real agents home, `.env`, and SSH key mounts are forbidden.
- Runtime images must be allowlisted and present locally; local `docker image inspect` remains required before any run.
- Sample mounts remain read-only; output mounts remain writable.
- Fake HOME and fake CODEX_HOME are required with a sanitized subprocess environment.
- Real tokens must not be passed to containers.
- Codex / codex exec, uploaded scripts, install commands, `shell=True`, and `eval` remain forbidden.
- Runtime command builders require `--cap-drop ALL`, `--security-opt no-new-privileges`, pids, memory, CPU, timeout, and read-only rootfs controls.
- Stage 22 adds `code/platforms/codex/enforcer/hardening/runtime_audit_schema.json` and runtime audit fields for policy version, no-new-privileges, cap-drop, read-only rootfs, local image preflight, sanitized env, and final verdict completeness.
- Read-only rootfs is enabled in the current command builders; no Stage 22 read-only-rootfs hardening gap is recorded.
- This remains a research prototype, not a production security system.
## Stage 23 Low-risk Real Skill Dynamic Monitoring Batch / Repeatability

Stage 23 prepares repeatable controlled monitoring for real skills that are already C0 H0 M0 L0 I0. The only allowed samples are `ideation.zip` and `react-effect-patterns.zip`.

- Completed result: `ideation.zip` and `react-effect-patterns.zip` each completed 2 rounds of batch benign monitoring.
- `implementation-guide.zip` remained blocked; `logging-best-practices.zip` and `val-town-cli.zip` remained manual review and were not run.
- Every completed round recorded `container_started=true`, `container_removed=true`, `network_mode=none`, `runtime_image=python:3.11-slim`, `image_allowlisted=true`, `image_present_locally=true`, and `docker_pull_executed=false`.
- Every completed round used sample read-only mount, writable output mount, fake HOME, fake CODEX_HOME, and sanitized subprocess env.
- Every completed round recorded no docker.sock, no privileged mode, no network host, no real token passthrough, no Codex / codex exec, no strace, and no real skill script execution.
- `analysis_results/real_skill_dynamic_monitoring_batch/repeatability_report.md` has been generated.
- `implementation-guide.zip`, `logging-best-practices.zip`, and `val-town-cli.zip` remain excluded from Stage 23.
- Real skill scripts are not executed.
- Codex / codex exec is not run.
- strace is not run.
- Network remains disabled with Docker `--network none`.
- Real tokens are not passed.
- docker.sock is not mounted.
- Privileged mode and network host mode are forbidden.
- Docker image pulls are forbidden; local image inspect is required before Docker run.
- Monitoring is limited to benign file tree, SKILL.md, metadata, and runtime audit fields.
- Batch output is written to `analysis_results/real_skill_dynamic_monitoring_batch/` as `summary.json`, `report.md`, `risk_table.csv`, and `repeatability_report.md`.
- This remains a research prototype, not a production security system.
## Stage 24 Synthetic Runtime Violation Live Test

Stage 24 validates runtime violation classification, response decisions, and report generation using synthetic runtime events only.

- No real malicious sample is run.
- No real attack command is executed.
- No Docker command is executed.
- No Codex / codex exec is run.
- No strace is run.
- No real skill is executed.
- Synthetic events use a fake container name and fake kill callback.
- docker.sock access is classified as CRITICAL.
- privileged container and host network requests are classified as CRITICAL.
- real token exposure, SSH key reads, real Codex HOME reads, and real agents HOME reads are classified as CRITICAL.
- outbound network attempts, uploaded script execution attempts, Docker pull attempts, Codex exec attempts, and strace attempts are classified as HIGH.
- CRITICAL/HIGH findings trigger kill_container or fail_closed.
- MEDIUM findings trigger fail_closed.
- LOW findings are record_only.
- Generated outputs: `analysis_results/runtime_violation_synthetic_live/summary.json`, `violation_event.json`, `violation_report.json`, `report.md`, and `risk_table.csv`.
- The Stage 24 run completed with `final_status=pass`, `fake_kill_callback_called=true`, and `real_container_killed=false`.
- This remains a research prototype, not a production security system.
## Stage 25A Agent-assisted Static Analysis Prototype

Stage 25A adds a pluggable agent-assisted static analysis prototype. It is an auxiliary layer, not the final decision maker.

- The deterministic static scanner remains the baseline.
- Agent-assisted analysis can add findings or raise risk, but it cannot lower deterministic scanner risk.
- HIGH / CRITICAL findings still require Dynamic Gate denied.
- Agent failure, timeout, or invalid output cannot automatically allow dynamic execution.
- Skill content is untrusted input.
- Prompt injection is a primary review target.
- Default provider is `mock`; it does not call a real API.
- Codex and Claude providers are placeholders only.
- Any future real provider must use redacted inputs, human approval, and must not send tokens, SSH keys, `.env`, real HOME, or sensitive host data.
- Stage 25A did not run Docker, Codex / codex exec, Claude Code, strace, or real skill scripts.
- Outputs are written under `analysis_results/agent_static_analysis/`.
- This remains a research prototype, not a production security system.
## Big Stage 25 Controlled Skill Activation Layer

Big Stage 25 begins the design of a controlled skill activation layer. The current implementation is plan-only and does not execute activation commands.

- Only C0 H0 M0 L0 I0 samples with no agent aggregate HIGH / CRITICAL risk can enter.
- Current allowed samples: `ideation.zip`, `react-effect-patterns.zip`.
- `implementation-guide.zip`, `logging-best-practices.zip`, and `val-town-cli.zip` remain rejected.
- The current run generated activation plans only; no Docker activation was run.
- Safe entrypoints are limited to `help`, `--help`, `version`, `--version`, `dry-run`, `--dry-run`, `metadata`, `inspect`, and `list`.
- `install.sh`, `setup.sh`, `run_skill.sh`, package installs, curl, wget, shell execution, docker.sock, token access, Codex, Claude Code, strace, and uploaded scripts remain forbidden.
- Future activation requires explicit human approval and must preserve no-network Docker, local image inspect, no Docker pull, fake HOME, fake CODEX_HOME, sanitized env, no docker.sock, no privileged mode, no network host, and runtime audit.
- Outputs are in `analysis_results/controlled_skill_activation/`.
- This remains a research prototype, not a production system.
## Big Stage 26 Document-Behavior Divergence Analysis Layer

Stage 26 compares each real skill's public `SKILL.md` description with already collected behavior evidence: deterministic static scan findings, agent static analysis, dynamic benign monitoring evidence, runtime audit evidence, controlled activation plans, and synthetic runtime violation policy evidence.

This stage does not execute skills, run Docker, run Codex or Claude Code, run strace, call real APIs, or enable network access. It analyzes all 5 real skills and identifies shadow features, undisclosed network / credential / filesystem / docker / install / execution behavior, and hidden prompt-injection indicators.

Outputs are written to `analysis_results/doc_behavior_divergence/summary.json`, `report.md`, `risk_table.csv`, `divergence_matrix.json`, and `manual_review_queue.md`. HIGH / CRITICAL divergence enters human security review, MEDIUM divergence enters manual review, and document-behavior divergence may raise final risk but cannot lower existing risk. This remains a research prototype, not a production security system.
## Big Stage 27 Scaled Validation and Final Reporting Layer

Stage 27 is the scaled validation and final reporting layer. It builds a local synthetic benign / suspicious / attack-like corpus, incorporates the existing results for the 5 real skills, and generates formal evaluation artifacts.

This stage does not execute real skills, run Docker, run Codex or Claude Code, run strace, call real APIs, or enable network access. Attack-like synthetic samples contain only fake token / fake env / fake ssh / fake docker.sock placeholder strings.

Outputs include `summary.json`, `risk_table.csv`, `metrics.json`, `confusion_matrix.json`, `manual_review_queue.md`, `final_research_report.md`, and `dashboard_data.json`. Metrics include TP / TN / FP / FN / precision / recall / f1. Suspicious samples are tracked separately as manual-review targets. This remains a research prototype, not a production security system.
## Big Stage 28: Controlled Sinkhole Network + Canary Honeypot + Multi-Session Dynamic Evidence

Stage 28 adds a controlled local sinkhole, fake canary credentials, multi-session evidence, and Codex platform attack-surface monitoring. It records requested host/path/header/body previews, fake credential touch/exfiltration indicators, delayed multi-session behavior, platform config touches, shadow features, and final dynamic verdicts.

This stage does not provide real internet access, execute high-risk real skills, run Docker, run Codex or Claude Code, run strace, call real APIs, mount docker.sock, use privileged containers, or read real `~/.codex`, `~/.agents`, `.env`, or SSH keys. Canary credentials are fake strings only.

Outputs are written to `analysis_results/controlled_sinkhole_dynamic/`: `summary.json`, `report.md`, `risk_table.csv`, `dynamic_evidence.json`, `sinkhole_requests.json`, `honeypot_events.json`, `multi_session_report.json`, `platform_surface_events.json`, and `final_dynamic_report.md`. This remains a research prototype, not a production system.
## Big Stage 29 Human Review and Vulnerability Labeling Layer

Stage 29 does not add new detection execution capability. It consolidates Stage 24-28 evidence into human review cards, vulnerability taxonomy labels, kill chain phases, recommended verdicts, and final label datasets.

The generated `manual_verdict` field is intentionally blank and waits for human reviewers. Synthetic attack-like samples are validation fixtures only and are not treated as real-world malicious conclusions. Real skill conclusions must remain evidence-based and subject to human review.

This stage does not run Docker, Codex or Claude Code, strace, real skills, real APIs, or network access. It remains a research prototype, not a production system.
