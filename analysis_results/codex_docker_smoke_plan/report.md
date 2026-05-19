# Codex Docker Safe Smoke Plan

- plan_only: `True`
- docker_build_allowed: `False`
- docker_run_allowed: `False`
- codex_exec_allowed: `False`
- network_mode: `none`
- sample_mount_mode: `read-only`
- output_mount_mode: `writable`
- fake_home_inside_container: `/home/codexsafe`
- fake_codex_home_inside_container: `/home/codexsafe/.codex`
- command_preview: `DISABLED: docker run --network none -e HOME=/home/codexsafe -e CODEX_HOME=/home/codexsafe/.codex -v /home/empty/Desktop/MaliciousAgentSkillsBench-Codex/code/platforms/codex/examples/safe_skill:/workspace/safe_skill:ro -v /home/empty/Desktop/MaliciousAgentSkillsBench-Codex/analysis_results/codex_docker_smoke_plan:/output:rw -v /usr/local/bin/codex:/usr/local/bin/codex:ro codex-safe-smoke:plan-only codex exec --sandbox read-only --ask-for-approval never`
- preflight_ok: `True`
- errors: `[]`
- warnings: `[]`

当前 Docker smoke plan 没有 build 镜像、没有启动容器、没有执行 Codex。
