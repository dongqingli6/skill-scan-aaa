# Big Stage 26 Document-Behavior Divergence Analysis Layer

This module compares the public claims in each real skill's `SKILL.md` with already collected static, agent, dynamic monitoring, runtime audit, controlled activation plan, and synthetic violation evidence.

Safety boundaries:

- It treats `SKILL.md` as untrusted input.
- It reads zip members and report files only.
- It does not execute skills or uploaded scripts.
- It does not run Docker, Codex, Claude Code, strace, or real APIs.
- It does not enable network access.

Outputs are written to `analysis_results/doc_behavior_divergence/`:

- `summary.json`
- `report.md`
- `risk_table.csv`
- `divergence_matrix.json`
- `manual_review_queue.md`
