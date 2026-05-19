# Agent-assisted Static Analysis Report

- agent_name: `stage25a-mock`
- analysis_mode: `agent_assisted_static_only`
- sample_name: `logging-best-practices.zip`
- recommended_gate: `manual_review`
- can_execute_dynamically: `false`
- requires_human_review: `true`
- agent_failed: `false`
- parse_error: `false`
- timeout: `false`
- risk_summary: `C0 H0 M1 L0 I0`

## Findings

- `medium` `manual_review_network_reference` in `SKILL.md`: Mock agent keeps network-related documentation under manual review.

## Notes

mock provider only; no real API call for logging-best-practices.zip
