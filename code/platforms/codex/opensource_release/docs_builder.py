from __future__ import annotations

from pathlib import Path


DOCS = {
    "ARCHITECTURE.md": "# Architecture\n\nThe pipeline is static-first: intake, deterministic scan, mock agent analysis, divergence analysis, controlled evidence, human review labels, and sanitized release artifacts.\n",
    "SAFETY_MODEL.md": "# Safety Model\n\nNo real malicious skill execution, no Docker by default, no Codex/Claude execution, no strace, no real API calls, no real credentials, and no network access in default tests.\n",
    "STAGE_OVERVIEW.md": "# Stage Overview\n\nStages 24-29 produce synthetic runtime evidence, controlled activation plans, divergence analysis, scaled validation, controlled sinkhole evidence, and human review labels.\n",
    "QUICK_START.md": "# Quick Start\n\nRun static-only tests and the release packaging CLI. Do not provide real API keys.\n",
    "DEMO_GUIDE.md": "# Demo Guide\n\nShow README, safety model, sanitized metrics, review cards, and public artifacts.\n",
    "OPEN_SOURCE_NOTES.md": "# Open Source Notes\n\nRaw real skill archives and unredacted analysis material are excluded from public release.\n",
    "COMPETITION_OVERVIEW.md": "# Competition Overview\n\nThis project demonstrates safe evaluation of agent skills with explainable evidence and human review outputs.\n",
    "FAQ.md": "# FAQ\n\n## Does it execute malicious skills?\n\nNo, not by default.\n\n## Are providers real?\n\nMock/static provider paths are default for public demos.\n",
    "LIMITATIONS.md": "# Limitations\n\nResearch prototype only. Static and synthetic evidence do not replace production-grade security review.\n",
    "ROADMAP.md": "# Roadmap\n\nImprove schemas, fixtures, review UI, and separately approved isolated smoke testing.\n",
}


def build_docs(repo_root: Path) -> list[str]:
    docs = repo_root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    generated = []
    for name, content in DOCS.items():
        path = docs / name
        path.write_text(content, encoding="utf-8")
        generated.append(str(path.relative_to(repo_root)))
    return generated
