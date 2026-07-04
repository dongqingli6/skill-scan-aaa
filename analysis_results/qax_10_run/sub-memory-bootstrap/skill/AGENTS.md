# Repository Instructions

## Safety

- Stay inside this repository unless the task requires another workspace path.
- Ask before destructive commands or OS-level changes.
- Do not modify macOS system settings, security settings, or global machine preferences.

<!-- BEGIN SUB-MEMORY MCP RULES -->
## sub_memory MCP

- If the `sub_memory` MCP server is available, call `get_memory_status` before implementation, debugging, review, or planning tasks that may depend on prior project memory.
- Use `recall_associated_memory` before answering when prior design decisions, integration history, or TODO context may matter.
- After each substantive turn, call `store_memory` with the latest user request and the final assistant answer or a faithful summary of it, unless the turn is empty, purely mechanical, or the current runtime already stores it automatically.
- Use `reinforce_memory` after the answer when recalled memory materially influenced the final answer or code change.
- When a multi-turn session gets long or repetitive, compact the active thread into a short working summary and continue from that summary plus `sub_memory` recall instead of depending on the full raw transcript.
- If `sub_memory` tools are missing in the current Codex session, explain that project-scoped MCP registration is stored in `.codex/config.toml` and that starting a new Codex session from the repository root may be required after running `sub-memory-bootstrap`.
<!-- END SUB-MEMORY MCP RULES -->
