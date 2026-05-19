# Stage 27 Manual Review Queue

## implementation-guide.zip
- sample_type: real
- family: real
- final_severity: high
- gate: blocked
- divergence: high
- recommendation: HIGH / CRITICAL divergence: blocked pending human security review.

## logging-best-practices.zip
- sample_type: real
- family: real
- final_severity: medium
- gate: manual_review
- divergence: none
- recommendation: No document-behavior divergence found in existing evidence; existing risk gates still apply.

## val-town-cli.zip
- sample_type: real
- family: real
- final_severity: medium
- gate: manual_review
- divergence: none
- recommendation: No document-behavior divergence found in existing evidence; existing risk gates still apply.

## attack_docker_sock_reference_skill.zip
- sample_type: synthetic
- family: attack_like
- final_severity: critical
- gate: blocked
- divergence: none
- recommendation: Block and send to human security review.

## attack_fake_env_exfil_skill.zip
- sample_type: synthetic
- family: attack_like
- final_severity: critical
- gate: blocked
- divergence: critical
- recommendation: Block and send to human security review.

## attack_fake_ssh_key_read_skill.zip
- sample_type: synthetic
- family: attack_like
- final_severity: critical
- gate: blocked
- divergence: none
- recommendation: Block and send to human security review.

## attack_prompt_injection_ignore_policy_skill.zip
- sample_type: synthetic
- family: attack_like
- final_severity: critical
- gate: blocked
- divergence: critical
- recommendation: Block and send to human security review.

## suspicious_broad_filesystem_skill.zip
- sample_type: synthetic
- family: suspicious
- final_severity: high
- gate: manual_review
- divergence: high
- recommendation: Send to manual review before any later runtime stage.

## suspicious_network_hint_skill.zip
- sample_type: synthetic
- family: suspicious
- final_severity: medium
- gate: manual_review
- divergence: none
- recommendation: Send to manual review before any later runtime stage.

## suspicious_obfuscated_instruction_skill.zip
- sample_type: synthetic
- family: suspicious
- final_severity: high
- gate: manual_review
- divergence: none
- recommendation: Send to manual review before any later runtime stage.

## suspicious_shell_hint_skill.zip
- sample_type: synthetic
- family: suspicious
- final_severity: high
- gate: manual_review
- divergence: high
- recommendation: Send to manual review before any later runtime stage.
