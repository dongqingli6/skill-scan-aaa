from __future__ import annotations

from pathlib import Path


def build_demo_materials(repo_root: Path) -> list[str]:
    files = {
        "demo/README.md": "# Demo\n\nUse this folder for safe, sanitized competition demos.\n",
        "demo/demo_script.md": "# Demo Script\n\n## 30 seconds\nIntroduce the agent skill security problem.\n\n## 1 minute\nExplain the layered architecture.\n\n## 2 minutes\nShow sanitized metrics, review cards, and sinkhole evidence.\n\n## 1 minute\nExplain safety boundaries.\n\n## 1 minute\nShow results and next steps.\n\n## Closing\nThis is a defensive research prototype for safer agent ecosystems.\n",
        "demo/demo_flow.md": "# Demo Flow\n\n1. Open README.\n2. Show architecture docs.\n3. Show public artifacts.\n4. Show review cards.\n5. Show safety model.\n",
        "demo/screenshots/README.md": "# Screenshots\n\nPlace sanitized screenshots here before submission.\n",
        "demo/sample_outputs/README.md": "# Sample Outputs\n\nUse files from `public_artifacts/` for safe demos.\n",
    }
    generated = []
    for rel, content in files.items():
        path = repo_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        generated.append(rel)
    return generated
