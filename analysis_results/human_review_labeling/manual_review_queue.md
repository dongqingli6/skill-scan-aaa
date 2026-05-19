# Stage 29 Manual Review Queue

## implementation-guide.zip
- source_type: real
- severity: HIGH
- recommended_verdict: blocked
- taxonomy_labels: `BLOCKED_BY_POLICY, DOC_BEHAVIOR_DIVERGENCE, NET_ATTEMPT, TOKEN_PATTERN`
- kill_chain_phases: `Initial Skill Load, Credential Access, Policy Blocked`
- manual_verdict: ``

## logging-best-practices.zip
- source_type: real
- severity: MEDIUM
- recommended_verdict: manual_review_required
- taxonomy_labels: `MANUAL_REVIEW_REQUIRED`
- kill_chain_phases: `Initial Skill Load, Manual Review`
- manual_verdict: ``

## val-town-cli.zip
- source_type: real
- severity: MEDIUM
- recommended_verdict: manual_review_required
- taxonomy_labels: `MANUAL_REVIEW_REQUIRED`
- kill_chain_phases: `Initial Skill Load, Manual Review`
- manual_verdict: ``

## attack_docker_sock_reference_skill.zip
- source_type: synthetic
- severity: CRITICAL
- recommended_verdict: blocked
- taxonomy_labels: `BLOCKED_BY_POLICY`
- kill_chain_phases: `Initial Skill Load, Policy Blocked`
- manual_verdict: ``

## attack_fake_env_exfil_skill.zip
- source_type: synthetic
- severity: CRITICAL
- recommended_verdict: blocked
- taxonomy_labels: `BLOCKED_BY_POLICY`
- kill_chain_phases: `Initial Skill Load, Policy Blocked`
- manual_verdict: ``

## attack_fake_ssh_key_read_skill.zip
- source_type: synthetic
- severity: CRITICAL
- recommended_verdict: blocked
- taxonomy_labels: `BLOCKED_BY_POLICY, SSH_KEY_ACCESS`
- kill_chain_phases: `Initial Skill Load, Credential Access, Policy Blocked`
- manual_verdict: ``

## attack_prompt_injection_ignore_policy_skill.zip
- source_type: synthetic
- severity: CRITICAL
- recommended_verdict: blocked
- taxonomy_labels: `BLOCKED_BY_POLICY, PROMPT_INJECTION`
- kill_chain_phases: `Initial Skill Load, Prompt Injection / Instruction Hijack, Policy Blocked`
- manual_verdict: ``

## suspicious_broad_filesystem_skill.zip
- source_type: synthetic
- severity: HIGH
- recommended_verdict: blocked
- taxonomy_labels: `MANUAL_REVIEW_REQUIRED`
- kill_chain_phases: `Initial Skill Load, Manual Review`
- manual_verdict: ``

## suspicious_network_hint_skill.zip
- source_type: synthetic
- severity: MEDIUM
- recommended_verdict: manual_review_required
- taxonomy_labels: `MANUAL_REVIEW_REQUIRED, NET_ATTEMPT`
- kill_chain_phases: `Initial Skill Load, Manual Review`
- manual_verdict: ``

## suspicious_obfuscated_instruction_skill.zip
- source_type: synthetic
- severity: HIGH
- recommended_verdict: blocked
- taxonomy_labels: `MANUAL_REVIEW_REQUIRED`
- kill_chain_phases: `Initial Skill Load, Manual Review`
- manual_verdict: ``

## suspicious_shell_hint_skill.zip
- source_type: synthetic
- severity: HIGH
- recommended_verdict: blocked
- taxonomy_labels: `MANUAL_REVIEW_REQUIRED, SHELL_EXEC`
- kill_chain_phases: `Initial Skill Load, Execution, Manual Review`
- manual_verdict: ``

## synthetic_canary_exfiltration_skill.zip
- source_type: synthetic
- severity: HIGH
- recommended_verdict: blocked
- taxonomy_labels: `BLOCKED_BY_POLICY, CODEX_HOME_TOUCH, CRED_ACCESS, CRED_EXFIL, ENV_ACCESS, MULTI_SESSION_STATE, NET_ATTEMPT, NET_EXFIL, SHADOW_FEATURE, SINKHOLE_TOUCH, SSH_KEY_ACCESS`
- kill_chain_phases: `Initial Skill Load, Credential Access, Platform Configuration Access, Persistence, Exfiltration, Policy Blocked`
- manual_verdict: ``

## synthetic_delayed_trigger_skill.zip
- source_type: synthetic
- severity: HIGH
- recommended_verdict: manual_review_required
- taxonomy_labels: `CODEX_HOME_TOUCH, CRED_ACCESS, DELAYED_TRIGGER, ENV_ACCESS, MANUAL_REVIEW_REQUIRED, MULTI_SESSION_STATE, NET_ATTEMPT, SHADOW_FEATURE, SINKHOLE_TOUCH, SSH_KEY_ACCESS`
- kill_chain_phases: `Initial Skill Load, Credential Access, Platform Configuration Access, Persistence, Exfiltration, Manual Review`
- manual_verdict: ``

## synthetic_platform_config_touch_skill.zip
- source_type: synthetic
- severity: HIGH
- recommended_verdict: blocked
- taxonomy_labels: `APPROVAL_POLICY_TOUCH, BLOCKED_BY_POLICY, CODEX_HOME_TOUCH, MULTI_SESSION_STATE, NET_ATTEMPT, PLATFORM_CONFIG_WRITE, SHADOW_FEATURE`
- kill_chain_phases: `Initial Skill Load, Platform Configuration Access, Persistence, Policy Blocked`
- manual_verdict: ``
