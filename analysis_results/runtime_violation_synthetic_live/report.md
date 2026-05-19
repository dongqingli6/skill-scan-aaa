# Stage 24 Synthetic Runtime Violation Live Test

This report is generated from synthetic runtime events and a fake kill callback only.

- total_events: `10`
- critical: `4`
- high: `6`
- medium: `0`
- low: `0`
- kill_decisions: `4`
- fail_closed_decisions: `6`
- record_only_decisions: `0`
- fake_kill_callback_called: `true`
- real_container_killed: `false`
- docker_executed: `false`
- codex_executed: `false`
- strace_executed: `false`
- real_skill_executed: `false`
- network_enabled: `false`
- final_status: `pass`

## Findings

- `docker_socket_access`: severity `CRITICAL`, action `kill_container`, response `kill_container`
- `outbound_network_attempt`: severity `HIGH`, action `fail_closed`, response `fail_closed`
- `real_token_exposure`: severity `CRITICAL`, action `kill_container`, response `kill_container`
- `forbidden_path_read`: severity `HIGH`, action `fail_closed`, response `fail_closed`
- `uploaded_script_execution_attempt`: severity `HIGH`, action `fail_closed`, response `fail_closed`
- `privileged_container_requested`: severity `CRITICAL`, action `kill_container`, response `kill_container`
- `host_network_requested`: severity `CRITICAL`, action `kill_container`, response `kill_container`
- `docker_pull_attempt`: severity `HIGH`, action `fail_closed`, response `fail_closed`
- `codex_exec_attempt`: severity `HIGH`, action `fail_closed`, response `fail_closed`
- `strace_attempt`: severity `HIGH`, action `fail_closed`, response `fail_closed`
