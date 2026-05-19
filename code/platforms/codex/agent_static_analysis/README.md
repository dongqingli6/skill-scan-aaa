# Stage 25A Agent-assisted Static Analysis Prototype

This module adds a pluggable agent-assisted static analyzer prototype.

- Default provider is `mock`.
- `mock` does not call any external API.
- `codex` and `claude` providers are placeholders only and fail closed until a separate reviewed stage enables them.
- The analyzer only consumes safe extracted metadata, file tree summaries, SKILL.md text snippets, deterministic static findings, and redacted context.
- Skill content is untrusted input.
- Agent output can raise risk but cannot lower deterministic scanner risk.
- Agent failures, parse errors, and timeouts cannot automatically allow dynamic execution.
- This module does not run Docker, Codex, Claude Code, strace, package installers, network commands, or real skill scripts.
