# Big Stage 28 Controlled Sinkhole Dynamic Evidence

- real_internet_enabled: false
- docker_executed: false
- codex_executed: false
- claude_code_executed: false
- strace_executed: false
- real_api_called: false
- real_skill_scripts_executed: false

## Samples

### ideation.zip
- final_verdict: `benign_controlled`
- honeypot_touched: `False`
- honeypot_exfiltrated: `False`
- multi_session_triggered: `True`
- platform_config_touched: `False`
- shadow_features: `[]`

### react-effect-patterns.zip
- final_verdict: `benign_controlled`
- honeypot_touched: `False`
- honeypot_exfiltrated: `False`
- multi_session_triggered: `True`
- platform_config_touched: `False`
- shadow_features: `[]`

### synthetic_canary_exfiltration_skill.zip
- final_verdict: `high_risk`
- honeypot_touched: `True`
- honeypot_exfiltrated: `True`
- multi_session_triggered: `True`
- platform_config_touched: `False`
- shadow_features: `["canary_exfiltration_intent", "honeypot_read_intent"]`

### synthetic_delayed_trigger_skill.zip
- final_verdict: `suspicious`
- honeypot_touched: `True`
- honeypot_exfiltrated: `False`
- multi_session_triggered: `True`
- platform_config_touched: `False`
- shadow_features: `["honeypot_read_intent"]`

### synthetic_platform_config_touch_skill.zip
- final_verdict: `high_risk`
- honeypot_touched: `False`
- honeypot_exfiltrated: `False`
- multi_session_triggered: `True`
- platform_config_touched: `True`
- shadow_features: `["platform_config_touch"]`
