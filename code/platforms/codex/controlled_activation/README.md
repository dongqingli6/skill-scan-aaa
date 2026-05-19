# Big Stage 25 Controlled Skill Activation Layer

This module prepares a controlled skill activation layer for low-risk real skills.

- Current allowed samples: `ideation.zip`, `react-effect-patterns.zip`.
- Forbidden samples: `implementation-guide.zip`, `logging-best-practices.zip`, `val-town-cli.zip`.
- The default workflow is plan-only and does not run Docker.
- Real activation requires explicit human approval in a later step.
- Allowed activation commands are limited to `help`, `--help`, `version`, `--version`, `dry-run`, `--dry-run`, `metadata`, `inspect`, and `list`.
- Unsafe patterns such as curl, wget, install commands, shell execution, docker.sock, real token names, `.env`, and SSH key paths are denied.
- Future runtime activation must remain no-network, read-only sample, writable output, fake HOME, fake CODEX_HOME, sanitized env, no docker.sock, no privileged mode, no network host, no Codex, no Claude Code, no strace, and no uploaded script execution.

This is a research prototype, not a production activation system.
