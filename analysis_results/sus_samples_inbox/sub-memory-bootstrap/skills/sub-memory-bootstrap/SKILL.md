---
name: sub-memory-bootstrap
description: Use when the user wants to install or validate the local sub-memory project, finish project-scoped Codex MCP registration, update AGENTS.md with sub_memory usage rules, start or inspect the shared local MCP daemon, start the local web UI, or generate ready-to-paste Codex, Gemini CLI, and Claude Code config snippets.
---

# Sub-memory Bootstrap

Use this skill for end-to-end local onboarding of the `sub-memory` repository.
If the installed skill does not include a full repository checkout, it must clone a managed
checkout into `$CODEX_HOME/repos/sub-memory-bootstrap`
or `~/.codex/repos/sub-memory-bootstrap` before bootstrapping.

## Workflow

1. Resolve the repository root from one of these sources:
   an explicit project path, the installed full-repo skill copy, or a managed checkout created
   under `$CODEX_HOME/repos/sub-memory-bootstrap` (fallback `~/.codex/repos/sub-memory-bootstrap`).
   Confirm these files exist:
   `requirements.txt`, `pyproject.toml`, `mcp_server.py`, `.env.example`
2. If the local install is missing or stale, run:
   `scripts/bootstrap_local.sh <repo-root>`
3. The bootstrap flow must also finish project-local Codex onboarding:
   write `.codex/config.toml` for `sub_memory` MCP registration and update `AGENTS.md`
   with `sub_memory` usage rules.
   Seed a new repository `AGENTS.md` from the bundled default template when needed.
4. Generate machine-specific config snippets with:
   `scripts/render_cli_snippets.py --project-dir <repo-root>`
5. Start or validate the shared MCP daemon with:
   `scripts/manage_mcp_daemon.sh {start|status|stop|restart} <repo-root>`
6. If the user asks for the web UI, start it with:
   `scripts/start_web_ui.sh <repo-root>`
   and report the browser URL.
7. Validate the install with:
   `sub-memory-agent --help`
   `sub-memory-mcp --help`
   `sub-memory-web --help`
   `python -m unittest discover -s tests`
8. Use project-scoped Codex configuration by default.
   Do not edit `~/.codex/config.toml`, `~/.gemini/settings.json`, `.mcp.json`, or other user-global config files without explicit permission.
9. For Codex sessions, the generated `AGENTS.md` rules should mirror the `local_agent`
   post-processing flow: recall before answering, store after each substantive turn,
   reinforce after the answer when recall materially helped, and compact long
   multi-turn sessions into a short working summary.
10. If the user is working in Korean, keep the explanation in Korean.
   Preserve commands, paths, config keys, and tool names exactly as written.

## What To Produce

- Local install status
- Exact shared MCP URL
- Exact `sub-memory-mcp` path
- Exact `sub-memory-web` path
- If started, the exact local browser URL
- Exact project Codex config path
- Confirmation that `AGENTS.md` contains the `sub_memory` usage rules
- Ready-to-paste snippets for:
  - Codex
  - Gemini CLI
  - Claude Code
- Any blockers such as missing `sqlite-vec`, missing `.env`, or incompatible Python

## Skill Installation

If the user wants this skill installed globally for Codex, copy or symlink this folder to:

- `$CODEX_HOME/skills/sub-memory-bootstrap`
- or `~/.codex/skills/sub-memory-bootstrap`

If only this nested skill folder is installed, the first bootstrap run must fetch the full
repository into the managed checkout path above so the install can proceed.

## Scope

- In scope: local install, shared MCP daemon, local web UI, CLI setup, verification, documentation snippets
- Out of scope: ChatGPT app, Gemini app, Claude app remote integrations

## Korean Prompt Examples

Use the same workflow for Korean-language requests such as:

- `sub-memory-bootstrap을 사용해서 이 저장소를 로컬에 설치하고 Codex, Gemini CLI, Claude Code 설정 스니펫까지 만들어줘.`
- `sub-memory-bootstrap으로 현재 설치 상태를 점검하고 이 저장소의 sub-memory-mcp 실제 경로를 알려줘.`
- `sub-memory-bootstrap으로 로컬 MCP 서버가 바로 쓸 수 있는 상태인지 확인하고, project-local Codex 설정과 AGENTS.md까지 준비해줘.`
- `sub-memory-bootstrap으로 이 저장소의 웹 UI를 실행하고 브라우저에서 열 주소를 알려줘.`
