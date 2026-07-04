#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def resolve_paths(project_dir: Path) -> dict[str, str]:
    project_dir = project_dir.resolve()
    script_dir = Path(__file__).resolve().parent
    venv_bin = project_dir / ".venv" / "bin"
    runtime_dir = Path.home() / ".codex" / "sub-memory"
    mcp_entrypoint = venv_bin / "sub-memory-mcp"
    daemon_script = script_dir / "manage_mcp_daemon.sh"
    mcp_url = "http://127.0.0.1:8766/mcp"
    skill_dir = project_dir / "skills" / "sub-memory-bootstrap"
    codex_config_path = project_dir / ".codex" / "config.toml"
    agents_path = project_dir / "AGENTS.md"
    configure_script = script_dir / "configure_codex_project.py"
    web_entrypoint = venv_bin / "sub-memory-web"
    web_start_script = script_dir / "start_web_ui.sh"

    return {
        "project_dir": str(project_dir),
        "runtime_dir": str(runtime_dir),
        "mcp_entrypoint": str(mcp_entrypoint),
        "daemon_script": str(daemon_script),
        "mcp_url": mcp_url,
        "web_entrypoint": str(web_entrypoint),
        "web_start_script": str(web_start_script),
        "skill_dir": str(skill_dir),
        "codex_config_path": str(codex_config_path),
        "agents_path": str(agents_path),
        "configure_script": str(configure_script),
    }


def build_output(paths: dict[str, str]) -> str:
    project_dir = paths["project_dir"]
    runtime_dir = paths["runtime_dir"]
    mcp_entrypoint = paths["mcp_entrypoint"]
    daemon_script = paths["daemon_script"]
    mcp_url = paths["mcp_url"]
    web_entrypoint = paths["web_entrypoint"]
    web_start_script = paths["web_start_script"]
    install_script = str(Path(daemon_script).with_name("install_shared_mcp.sh"))
    update_script = str(Path(daemon_script).with_name("update_shared_mcp.sh"))
    skill_dir = paths["skill_dir"]
    codex_config_path = paths["codex_config_path"]
    agents_path = paths["agents_path"]
    configure_script = paths["configure_script"]

    return f"""# sub-memory local onboarding snippets

## Codex project registration

First install:

```bash
{install_script} {project_dir}
```

Refresh an existing install:

```bash
{update_script} {project_dir}
```

```bash
python3 {configure_script} --project-dir {project_dir}
```

This writes:

- `{codex_config_path}`
- `{agents_path}`

## Codex

Start the shared MCP daemon first:

```bash
{daemon_script} start {project_dir}
```

```toml
[mcp_servers.sub_memory]
url = "{mcp_url}"
enabled_tools = ["recall_associated_memory", "store_memory", "reinforce_memory", "get_memory_status"]
startup_timeout_sec = 90
tool_timeout_sec = 120
```

## Gemini CLI

```json
{{
  "mcpServers": {{
    "sub_memory": {{
      "url": "{mcp_url}",
      "timeout": 30000
    }}
  }}
}}
```

## Claude Code

```bash
claude mcp add --transport http sub-memory {mcp_url}
```

## Codex skill install

```bash
mkdir -p ~/.codex/skills
cp -R {skill_dir} ~/.codex/skills/
```

or

```bash
mkdir -p ~/.codex/skills
ln -s {skill_dir} ~/.codex/skills/sub-memory-bootstrap
```

## Next step

Start a new Codex session from `{project_dir}` so the project-scoped MCP config and
`AGENTS.md` instructions are loaded together.

## Web UI

Shared MCP daemon status:

```bash
{daemon_script} status {project_dir}
```

Direct entrypoint:

```bash
{web_entrypoint} --base-dir {runtime_dir} --host 127.0.0.1 --port 8765
```

Helper script:

```bash
{web_start_script} {project_dir}
```

Browser URL:

```text
http://127.0.0.1:8765/ui
```
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render local sub-memory CLI snippets")
    parser.add_argument(
        "--project-dir",
        default=str(Path.cwd()),
        help="Repository root containing .venv and pyproject.toml.",
    )
    args = parser.parse_args()

    paths = resolve_paths(Path(args.project_dir))
    print(build_output(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
