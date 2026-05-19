from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_manifest(output_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    path_json = output_root / "open_source_release_manifest.json"
    path_md = output_root / "open_source_release_manifest.md"
    path_json.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path_md.write_text(_manifest_md(manifest), encoding="utf-8")
    return manifest


def _manifest_md(manifest: dict[str, Any]) -> str:
    lines = ["# Open Source Release Manifest", ""]
    lines.append("## Public Files Generated")
    for item in manifest.get("public_files_generated", []):
        lines.append(f"- `{item}`")
    lines.append("\n## Sensitive Files Excluded")
    for item in manifest.get("sensitive_files_excluded", [])[:100]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Checklist",
            "- README generated",
            "- docs generated",
            "- demo materials generated",
            "- competition materials generated",
            "- public artifacts sanitized",
            "- safe regression status recorded",
            "",
            "## Known Limitations",
            "Research prototype only; not a production security system.",
            "",
        ]
    )
    return "\n".join(lines)
