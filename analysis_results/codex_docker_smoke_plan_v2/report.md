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
- command_preview: `DISABLED: docker run --network none -e HOME=/home/codexsafe -e CODEX_HOME=/home/codexsafe/.codex -e PATH=/opt/codex-bundle/bin:/usr/local/bin:/usr/bin:/bin -v C:\Users\captivating\Pictures\MaliciousAgentSkillsBench-Codex\code\platforms\codex\examples\safe_skill:/workspace/safe_skill:ro -v C:\Users\captivating\Pictures\MaliciousAgentSkillsBench-Codex\analysis_results\codex_docker_smoke_plan_v2:/output:rw -v /opt/codex-bundle:/opt/codex-bundle:ro codex-safe-smoke:plan-only codex exec --sandbox read-only --ask-for-approval never`
- preflight_ok: `False`
- errors: `['output_mount must not be inside sample_mount']`
- warnings: `[]`

当前 Docker smoke plan 没有 build 镜像、没有启动容器、没有执行 Codex。
