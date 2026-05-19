# Big Stage 29 Human Review and Vulnerability Labeling Layer

## Sample-level Review Summary

- `implementation-guide.zip`: severity `HIGH`, recommended `blocked`, labels `BLOCKED_BY_POLICY, DOC_BEHAVIOR_DIVERGENCE, NET_ATTEMPT, TOKEN_PATTERN`
- `logging-best-practices.zip`: severity `MEDIUM`, recommended `manual_review_required`, labels `MANUAL_REVIEW_REQUIRED`
- `val-town-cli.zip`: severity `MEDIUM`, recommended `manual_review_required`, labels `MANUAL_REVIEW_REQUIRED`
- `ideation.zip`: severity `LOW`, recommended `benign`, labels `BENIGN_CONTROLLED, MULTI_SESSION_STATE`
- `react-effect-patterns.zip`: severity `LOW`, recommended `benign`, labels `BENIGN_CONTROLLED, MULTI_SESSION_STATE`
- `attack_docker_sock_reference_skill.zip`: severity `CRITICAL`, recommended `blocked`, labels `BLOCKED_BY_POLICY`
- `attack_fake_env_exfil_skill.zip`: severity `CRITICAL`, recommended `blocked`, labels `BLOCKED_BY_POLICY`
- `attack_fake_ssh_key_read_skill.zip`: severity `CRITICAL`, recommended `blocked`, labels `BLOCKED_BY_POLICY, SSH_KEY_ACCESS`
- `attack_prompt_injection_ignore_policy_skill.zip`: severity `CRITICAL`, recommended `blocked`, labels `BLOCKED_BY_POLICY, PROMPT_INJECTION`
- `benign_formatter_skill.zip`: severity `NONE`, recommended `benign`, labels `BENIGN_CONTROLLED`
- `benign_notes_skill.zip`: severity `NONE`, recommended `benign`, labels `BENIGN_CONTROLLED`
- `benign_readme_helper_skill.zip`: severity `NONE`, recommended `benign`, labels `BENIGN_CONTROLLED`
- `benign_writer_skill.zip`: severity `NONE`, recommended `benign`, labels `BENIGN_CONTROLLED`
- `suspicious_broad_filesystem_skill.zip`: severity `HIGH`, recommended `blocked`, labels `MANUAL_REVIEW_REQUIRED`
- `suspicious_network_hint_skill.zip`: severity `MEDIUM`, recommended `manual_review_required`, labels `MANUAL_REVIEW_REQUIRED, NET_ATTEMPT`
- `suspicious_obfuscated_instruction_skill.zip`: severity `HIGH`, recommended `blocked`, labels `MANUAL_REVIEW_REQUIRED`
- `suspicious_shell_hint_skill.zip`: severity `HIGH`, recommended `blocked`, labels `MANUAL_REVIEW_REQUIRED, SHELL_EXEC`
- `synthetic_canary_exfiltration_skill.zip`: severity `HIGH`, recommended `blocked`, labels `BLOCKED_BY_POLICY, CODEX_HOME_TOUCH, CRED_ACCESS, CRED_EXFIL, ENV_ACCESS, MULTI_SESSION_STATE, NET_ATTEMPT, NET_EXFIL, SHADOW_FEATURE, SINKHOLE_TOUCH, SSH_KEY_ACCESS`
- `synthetic_delayed_trigger_skill.zip`: severity `HIGH`, recommended `manual_review_required`, labels `CODEX_HOME_TOUCH, CRED_ACCESS, DELAYED_TRIGGER, ENV_ACCESS, MANUAL_REVIEW_REQUIRED, MULTI_SESSION_STATE, NET_ATTEMPT, SHADOW_FEATURE, SINKHOLE_TOUCH, SSH_KEY_ACCESS`
- `synthetic_platform_config_touch_skill.zip`: severity `HIGH`, recommended `blocked`, labels `APPROVAL_POLICY_TOUCH, BLOCKED_BY_POLICY, CODEX_HOME_TOUCH, MULTI_SESSION_STATE, NET_ATTEMPT, PLATFORM_CONFIG_WRITE, SHADOW_FEATURE`

## Taxonomy Distribution

{
  "APPROVAL_POLICY_TOUCH": 1,
  "BENIGN_CONTROLLED": 6,
  "BLOCKED_BY_POLICY": 7,
  "CODEX_HOME_TOUCH": 3,
  "CRED_ACCESS": 2,
  "CRED_EXFIL": 1,
  "DELAYED_TRIGGER": 1,
  "DOC_BEHAVIOR_DIVERGENCE": 1,
  "ENV_ACCESS": 2,
  "MANUAL_REVIEW_REQUIRED": 7,
  "MULTI_SESSION_STATE": 5,
  "NET_ATTEMPT": 5,
  "NET_EXFIL": 1,
  "PLATFORM_CONFIG_WRITE": 1,
  "PROMPT_INJECTION": 1,
  "SHADOW_FEATURE": 3,
  "SHELL_EXEC": 1,
  "SINKHOLE_TOUCH": 2,
  "SSH_KEY_ACCESS": 3,
  "TOKEN_PATTERN": 1
}

## Kill Chain Matrix

{
  "attack_docker_sock_reference_skill.zip": [
    "Initial Skill Load",
    "Policy Blocked"
  ],
  "attack_fake_env_exfil_skill.zip": [
    "Initial Skill Load",
    "Policy Blocked"
  ],
  "attack_fake_ssh_key_read_skill.zip": [
    "Initial Skill Load",
    "Credential Access",
    "Policy Blocked"
  ],
  "attack_prompt_injection_ignore_policy_skill.zip": [
    "Initial Skill Load",
    "Prompt Injection / Instruction Hijack",
    "Policy Blocked"
  ],
  "benign_formatter_skill.zip": [
    "Reconnaissance",
    "Initial Skill Load"
  ],
  "benign_notes_skill.zip": [
    "Reconnaissance",
    "Initial Skill Load"
  ],
  "benign_readme_helper_skill.zip": [
    "Reconnaissance",
    "Initial Skill Load"
  ],
  "benign_writer_skill.zip": [
    "Reconnaissance",
    "Initial Skill Load"
  ],
  "ideation.zip": [
    "Reconnaissance",
    "Initial Skill Load",
    "Persistence"
  ],
  "implementation-guide.zip": [
    "Initial Skill Load",
    "Credential Access",
    "Policy Blocked"
  ],
  "logging-best-practices.zip": [
    "Initial Skill Load",
    "Manual Review"
  ],
  "react-effect-patterns.zip": [
    "Reconnaissance",
    "Initial Skill Load",
    "Persistence"
  ],
  "suspicious_broad_filesystem_skill.zip": [
    "Initial Skill Load",
    "Manual Review"
  ],
  "suspicious_network_hint_skill.zip": [
    "Initial Skill Load",
    "Manual Review"
  ],
  "suspicious_obfuscated_instruction_skill.zip": [
    "Initial Skill Load",
    "Manual Review"
  ],
  "suspicious_shell_hint_skill.zip": [
    "Initial Skill Load",
    "Execution",
    "Manual Review"
  ],
  "synthetic_canary_exfiltration_skill.zip": [
    "Initial Skill Load",
    "Credential Access",
    "Platform Configuration Access",
    "Persistence",
    "Exfiltration",
    "Policy Blocked"
  ],
  "synthetic_delayed_trigger_skill.zip": [
    "Initial Skill Load",
    "Credential Access",
    "Platform Configuration Access",
    "Persistence",
    "Exfiltration",
    "Manual Review"
  ],
  "synthetic_platform_config_touch_skill.zip": [
    "Initial Skill Load",
    "Platform Configuration Access",
    "Persistence",
    "Policy Blocked"
  ],
  "val-town-cli.zip": [
    "Initial Skill Load",
    "Manual Review"
  ]
}

## Limitations

Stage 29 does not execute samples and does not replace human judgment. `manual_verdict` remains blank for reviewer input. Synthetic attack-like samples are validation fixtures, not real-world malicious conclusions.
