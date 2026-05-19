from __future__ import annotations

from pathlib import Path


MATERIALS = {
    "PROJECT_INTRO.md": "# 项目简介\n\n本项目是一个面向 AI Agent Skill 生态的防御性安全评估原型，重点解决 skill 包中的隐藏指令、凭据访问、联网外传、平台配置滥用和多轮触发风险。\n",
    "INNOVATION_POINTS.md": "# Innovation Points\n\nLayered static-first evaluation, document-behavior divergence, controlled sinkhole evidence, canary credentials, multi-session signals, and human review labels.\n",
    "TECHNICAL_ROUTE.md": "# Technical Route\n\nStatic scan -> mock agent analysis -> divergence -> synthetic runtime evidence -> controlled sinkhole/canary -> human review labels -> sanitized release package.\n",
    "DEMO_SCRIPT.md": "# Demo Script\n\nUse the demo script in `demo/demo_script.md` and focus on safe reproducibility.\n",
    "RESULTS_SUMMARY.md": "# Results Summary\n\nStage 29 labeled 20 samples with benign, blocked, and manual-review verdicts. Safe regression remains PASS 11/11.\n",
    "SAFETY_AND_ETHICS.md": "# Safety and Ethics\n\nNo real secrets, no real malicious execution, no real provider calls, and no raw sample release.\n",
    "FUTURE_WORK.md": "# Future Work\n\nLarger public fixture corpus, formal policy schema, UI polish, and independently approved isolated smoke tests.\n",
    "SUBMISSION_CHECKLIST.md": "# Submission Checklist\n\n- [ ] Confirm license.\n- [ ] Review public artifacts.\n- [ ] Add sanitized screenshots.\n- [ ] Verify no real secrets.\n- [ ] Run safe regression.\n",
}


def build_competition_pack(repo_root: Path) -> list[str]:
    root = repo_root / "competition_materials"
    root.mkdir(parents=True, exist_ok=True)
    generated = []
    for name, content in MATERIALS.items():
        path = root / name
        path.write_text(content, encoding="utf-8")
        generated.append(str(path.relative_to(repo_root)))
    return generated
