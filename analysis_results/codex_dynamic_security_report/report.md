# Codex Dynamic Security Report

- target_platform: codex
- sample: safe_skill
- docker_network_mode: none
- malicious_samples_executed: false
- real_tokens_present: false
- sample_mount: read-only
- output_mount: writable
- codex_bundle_mount: read-only

## Strace Summary

- parsed_file_count: 91
- execve: 175
- openat: 567
- socket: 17
- connect: 4

## Risk Summary

- LOW: 57
- MEDIUM: 0
- HIGH: 0
- CRITICAL: 0

## Final Verdict

safe_skill-only dynamic harness succeeded; observed Codex network attempts were blocked by Docker --network none; no HIGH/CRITICAL filesystem or credential access evidence was observed.
