# Web UI Safe Dynamic Execution Gate Plan

- Job ID: `job_20260510_034916_265e2a99`
- Eligibility: `denied`
- Reason: `blocked by dynamic gate`
- Dynamic execution performed: `false`
- Benign inspection only: `true`
- Uploaded scripts executed: `false`

## Required Controls

- no_network
- fake_home
- fake_codex_home
- readonly_sample_mount
- output_rw
- no_docker_sock
- no_privileged
- no_network_host
- no_real_token
- timeout
- policy_gate_required
- runtime_monitor_required
- kill_on_high_critical
- fail_closed_by_default

## Blockers

- safety boundary missing fake_home
