# Agent-assisted Static Analysis Report

- agent_name: `stage25a-mock`
- analysis_mode: `agent_assisted_static_only`
- sample_name: `implementation-guide.zip`
- recommended_gate: `denied`
- can_execute_dynamically: `false`
- requires_human_review: `true`
- agent_failed: `false`
- parse_error: `false`
- timeout: `false`
- risk_summary: `C0 H4 M0 L0 I0`

## Findings

- `high` `network_or_credential_example` in `/home/empty/Desktop/MaliciousAgentSkillsBench-Codex/analysis_results/real_skill_intake/quarantine/implementation-guide_bd0788f86eab/uploaded_skill/implementation-guide/references/example-rate-limiting.md`: Mock agent confirms deterministic HIGH context requires blocking.

## Notes

mock provider only; no real API call for implementation-guide.zip
