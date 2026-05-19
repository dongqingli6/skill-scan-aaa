# Big Stage 27 Scaled Validation and Final Reporting Layer

## Executive Summary

Stage 27 evaluates 17 samples using static-only evidence aggregation: 5 real skills and 12 synthetic fixtures.

## System Overview

The pipeline combines deterministic static results, mock agent static aggregation, document-behavior divergence analysis, low-risk dynamic monitoring summaries, and synthetic runtime violation evidence.

## Safety Boundary

This stage does not execute skills, run container workloads, run Codex or Claude Code, run syscall tracing, call real APIs, or enable network access. Synthetic attack-like fixtures contain fake placeholders only.

## Dataset

Real skills: 5. Synthetic skills: 12 with benign, suspicious, and attack-like families.

## Real Skill Results

| Sample | Family | Severity | Gate |
|---|---|---|---|
| `implementation-guide.zip` | `real` | `high` | `blocked` |
| `logging-best-practices.zip` | `real` | `medium` | `manual_review` |
| `val-town-cli.zip` | `real` | `medium` | `manual_review` |
| `ideation.zip` | `real` | `none` | `allowed` |
| `react-effect-patterns.zip` | `real` | `none` | `allowed` |

## Synthetic Corpus Results

| Sample | Family | Severity | Gate |
|---|---|---|---|
| `attack_docker_sock_reference_skill.zip` | `attack_like` | `critical` | `blocked` |
| `attack_fake_env_exfil_skill.zip` | `attack_like` | `critical` | `blocked` |
| `attack_fake_ssh_key_read_skill.zip` | `attack_like` | `critical` | `blocked` |
| `attack_prompt_injection_ignore_policy_skill.zip` | `attack_like` | `critical` | `blocked` |
| `benign_formatter_skill.zip` | `benign` | `none` | `allowed` |
| `benign_notes_skill.zip` | `benign` | `none` | `allowed` |
| `benign_readme_helper_skill.zip` | `benign` | `none` | `allowed` |
| `benign_writer_skill.zip` | `benign` | `none` | `allowed` |
| `suspicious_broad_filesystem_skill.zip` | `suspicious` | `high` | `manual_review` |
| `suspicious_network_hint_skill.zip` | `suspicious` | `medium` | `manual_review` |
| `suspicious_obfuscated_instruction_skill.zip` | `suspicious` | `high` | `manual_review` |
| `suspicious_shell_hint_skill.zip` | `suspicious` | `high` | `manual_review` |

## Agent-assisted Static Analysis Results

Agent-assisted results are consumed from existing mock/static summaries; agent output cannot lower deterministic risk.

## Document-Behavior Divergence Results

Stage 26 evidence is included. Divergence can raise final risk but cannot lower existing risk.

## Runtime Synthetic Violation Results

Stage 24 synthetic runtime violation evidence is included as prior dynamic evidence; no new runtime execution is performed.

## Low-risk Dynamic Monitoring Results

Stage 23 low-risk monitoring evidence is included for previously approved benign inspection candidates only.

## Metrics

{
  "allowed_count": 6,
  "attack_like_count": 4,
  "benign_count": 4,
  "blocked_count": 5,
  "consistent_count": 6,
  "critical_count": 4,
  "divergence_count": 5,
  "f1": 1.0,
  "false_negative": 0,
  "false_positive": 0,
  "high_count": 4,
  "low_count": 0,
  "manual_review_count": 6,
  "medium_count": 3,
  "precision": 1.0,
  "real_skill_count": 5,
  "recall": 1.0,
  "suspicious_count": 4,
  "suspicious_manual_review_count": 4,
  "synthetic_count": 12,
  "total_samples": 17,
  "true_negative": 4,
  "true_positive": 4
}

## False Positives / False Negatives

FP=0; FN=0; suspicious samples are counted separately as manual-review targets.

## Manual Review Queue

See analysis_results/scaled_validation/manual_review_queue.md.

## Limitations

This is a research prototype. Static-only synthetic validation is useful for regression coverage but is not a production-grade security guarantee.

## Future Work

Add broader curated corpora, human-reviewed labels, richer static parsers, and separately approved controlled activation smoke tests.

## Conclusion

Stage 27 produces scaled static validation artifacts and a final research report while preserving the no-execution safety boundary.
