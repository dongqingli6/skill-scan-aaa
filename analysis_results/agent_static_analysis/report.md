# Stage 25A Agent-assisted Static Analysis Prototype

- provider: `mock`
- provider_is_mock: `true`
- total_samples: `5`
- denied_count: `1`
- manual_review_count: `2`
- allowed_for_manual_review_count: `2`
- docker_executed: `false`
- codex_executed: `false`
- claude_code_executed: `false`
- strace_executed: `false`
- real_skill_executed: `false`
- network_enabled: `false`
- final_status: `pass`

## Results

- `implementation-guide.zip`: deterministic `high`, agent `high`, final `high`, gate `denied`
- `logging-best-practices.zip`: deterministic `medium`, agent `medium`, final `medium`, gate `manual_review`
- `val-town-cli.zip`: deterministic `medium`, agent `medium`, final `medium`, gate `manual_review`
- `ideation.zip`: deterministic `none`, agent `none`, final `none`, gate `allowed_for_manual_review`
- `react-effect-patterns.zip`: deterministic `none`, agent `none`, final `none`, gate `allowed_for_manual_review`
